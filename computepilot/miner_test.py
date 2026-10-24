"""A40 host diagnostics and measured inference only; no miner activation or signing.

Standard library only. Run `python3 -m computepilot.miner_test --help`.
Evidence is operator-collected and unsigned, never a FLOP receipt.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "computepilot.miner-test.v12"
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
GPU_FIELDS = ["name", "memory.total", "memory.used", "utilization.gpu",
              "temperature.gpu", "power.draw", "driver_version"]
GPU_PROFILES = {
    "a40": (r"(?:NVIDIA )?A40", 44000),
    "a100-40": (r"(?:NVIDIA )?A100(?:-SXM4|-PCIE)?-40GB", 37000),
    "a100-80": (r"(?:NVIDIA )?A100(?:-SXM4|-PCIE)?-80GB", 74000),
}


def hardware_matches(gpus, target):
    pattern, minimum = GPU_PROFILES[target]
    # Whole-host capacity is relevant; never silently ignore additional cards/MIG.
    return len(gpus) == 1 and bool(re.fullmatch(pattern, gpus[0]['name'], re.I)) and (gpus[0]['memory.total'] or 0) >= minimum


def stamp():
    return datetime.now(timezone.utc).isoformat()


def envelope(kind, **data):
    return dict(schema=SCHEMA, kind=kind, collected_at=stamp(),
                evidence="LOCAL_OBSERVATION_UNSIGNED", simulated=False,
                flop_activity="NOT_VERIFIED", mining_activation="NOT_PERFORMED", **data)


def command(argv, timeout=20):
    """Never persist arbitrary stdout/stderr: callers select safe result fields."""
    if not shutil.which(argv[0]):
        return {"status": "MISSING", "returncode": None}, ""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return {"status": "PASS" if p.returncode == 0 else "FAIL",
                "returncode": p.returncode}, p.stdout if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "TIMEOUT_OR_OS_ERROR", "returncode": None}, ""


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def gpu_rows(output):
    rows = []
    for row in csv.reader(io.StringIO(output)):
        if len(row) != len(GPU_FIELDS):
            raise ValueError("Unexpected nvidia-smi column count")
        item = dict(zip(GPU_FIELDS, (s.strip() for s in row)))
        for key in GPU_FIELDS[1:-1]:
            item[key] = number(item[key])
        rows.append(item)
    return rows


def pinned_image(value):
    if not re.fullmatch(r"[a-zA-Z0-9./_:-]+@sha256:[0-9a-f]{64}", value):
        raise ValueError("Use the approved diagnostic image pinned by sha256 digest")
    return value


def preflight(cuda_image=None, target="a40"):
    probes = {}
    probes["nvidia_smi"], raw = command([
        "nvidia-smi", "--query-gpu=" + ",".join(GPU_FIELDS),
        "--format=csv,noheader,nounits"])
    try:
        gpus = gpu_rows(raw)
    except ValueError:
        gpus = []
        probes["nvidia_smi"]["status"] = "INVALID_OUTPUT"
    for key, argv in {
        "docker_client": ["docker", "--version"],
        "docker_server": ["docker", "info", "--format", "{{json .Runtimes}}"],
        "compose": ["docker", "compose", "version", "--short"],
        "nvidia_toolkit": ["nvidia-container-cli", "--version"],
        "ssh_client": ["ssh", "-V"],
    }.items():
        probes[key], value = command(argv)
        if key == "docker_server" and probes[key]["status"] == "PASS":
            try:
                probes[key]["nvidia_runtime_registered"] = "nvidia" in json.loads(value)
            except (ValueError, TypeError):
                probes[key]["status"] = "INVALID_OUTPUT"
    probes["docker_gpu"] = {"status": "NOT_RUN", "reason": "Approved CUDA image not supplied"}
    if cuda_image:
        pinned_image(cuda_image)
        probes["docker_gpu"], output = command([
            "docker", "run", "--rm", "--network=none", "--gpus", "all",
            cuda_image, "nvidia-smi", "--query-gpu=name,memory.total",
            "--format=csv,noheader,nounits"], timeout=180)
        try:
            container_gpus = [(r[0].strip(), float(r[1])) for r in csv.reader(io.StringIO(output))]
            host_gpus = [(g["name"], g["memory.total"]) for g in gpus]
            if not container_gpus or sorted(container_gpus) != sorted(host_gpus):
                probes["docker_gpu"]["status"] = "GPU_INVENTORY_MISMATCH"
        except (ValueError, IndexError):
            probes["docker_gpu"]["status"] = "INVALID_OUTPUT"
    host_ok = platform.system() == "Linux" and platform.machine() in ("x86_64", "amd64")
    # A40 ECC reservations can reduce reported usable memory below 48 GiB.
    a40_ok = hardware_matches(gpus, "a40")
    target_ok = hardware_matches(gpus, target)
    essentials = ["nvidia_smi", "docker_server", "compose", "docker_gpu"]
    ready = host_ok and target_ok and all(probes[k]["status"] == "PASS" for k in essentials)
    return envelope("preflight", host={"os": platform.system(), "arch": platform.machine(),
                    "cpu_count": os.cpu_count(), "disk_free_bytes": shutil.disk_usage(Path.cwd()).free},
                    gpus=gpus, probes=probes,
                    target_gpu=target, target_hardware="PASS" if target_ok else "NOT_CONFIRMED",
                    gpu_protocol_compatibility="NOT_VERIFIED",
                    target_a40_hardware="PASS" if a40_ok else "NOT_CONFIRMED",
                    host_prerequisites="PASS" if ready else "INCOMPLETE",
                    ssh_access="NOT_TESTED", model_identity="NOT_TESTED",
                    toploc="NOT_TESTED", registration="NOT_VERIFIED", calibration="NOT_VERIFIED")


def loopback_url(value):
    from urllib.parse import urlsplit
    u = urlsplit(value)
    if u.scheme != "http" or u.hostname not in ("localhost", "127.0.0.1", "::1") or u.username or u.password or u.query or u.fragment or u.path not in ("", "/"):
        raise ValueError("Use an HTTP loopback origin inside the backend container; no public API")
    return value.rstrip("/")


def fetch_text(base, route, token="", body=None, timeout=120):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + route, headers=headers,
                                 data=None if body is None else json.dumps(body).encode())
    # Ignore proxy environment; never send the inference key through a proxy or redirect.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(req, timeout=timeout) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Response exceeds 2 MB")
        return raw.decode('utf-8')


def fetch_json(base, route, token="", body=None, timeout=120):
    return json.loads(fetch_text(base, route, token, body, timeout))


def check_health(health, model_hash, policy_hash):
    return (isinstance(health, dict) and health.get("model_identity") == "measured" and
            health.get("model_hash") == model_hash and
            health.get("decode_policy_hash") == policy_hash and
            str(health.get("precision", "")).upper() == "BF16")


def validate_hash(value):
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", value):
        raise ValueError("Expected an operator-supplied 0x + 64 hex hash")
    return value


def benchmark(args):
    base = loopback_url(args.base)
    model_hash, policy_hash = validate_hash(args.model_hash), validate_hash(args.policy_hash)
    token = os.environ.get("INFERENCE_API_KEY", "")
    if not token:
        raise ValueError("INFERENCE_API_KEY must already exist inside the backend environment")
    health = fetch_json(base, "/health", token)
    if not check_health(health, model_hash, policy_hash):
        raise ValueError("Backend identity/precision/policy mismatch or unsupported health schema; stop")
    rows = []
    for i in range(args.warmup + args.requests):
        start = time.perf_counter()
        try:
            result = fetch_json(base, "/v1/chat/completions", token, {
                "model": MODEL, "messages": [{"role": "user", "content":
                "Explain in three sentences how to keep a GPU inference server reliable."}],
                "temperature": 0, "max_tokens": args.max_tokens, "stream": False})
            duration = time.perf_counter() - start
            text = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {}).get("completion_tokens")
            if result.get("model") != MODEL or not isinstance(text, str) or not text.strip():
                raise ValueError("Unexpected model or empty output")
            if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens <= 0:
                raise ValueError("Completion token count unavailable; cannot measure throughput")
            row = {"status": "PASS", "e2e_ms": round(duration * 1000, 3),
                   "completion_tokens": tokens, "output_sha256": hashlib.sha256(text.encode()).hexdigest()}
        except (KeyError, IndexError, TypeError, ValueError, OSError, urllib.error.URLError):
            row = {"status": "FAIL", "error": "INFERENCE_REQUEST_FAILED_OR_INVALID_RESPONSE"}
        row["warmup"] = i < args.warmup
        rows.append(row)
    measured = [r for r in rows if not r["warmup"]]
    passed = [r for r in measured if r["status"] == "PASS"]
    times = sorted(r["e2e_ms"] for r in passed)
    return envelope("benchmark", model=MODEL, model_hash=model_hash, policy_hash=policy_hash,
                    precision="BF16", model_identity="measured", warmup_requests=args.warmup,
                    requested=args.requests, successful=len(passed), failed=len(measured)-len(passed),
                    max_tokens=args.max_tokens, concurrency=1, rows=rows,
                    median_e2e_ms=statistics.median(times) if times else None,
                    p95_e2e_ms=times[math.ceil(.95*len(times))-1] if times else None,
                    output_tokens_per_e2e_second=(sum(r["completion_tokens"] for r in passed) /
                        (sum(times)/1000)) if times else None,
                    ttft_ms=None, throughput_scope="Output tokens / full request time, includes prefill; not decode-only",
                    toploc="NOT_VERIFIED", registration="NOT_VERIFIED", calibration="NOT_VERIFIED")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.write("\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    for name in ("preflight", "monitor", "ssh-preflight", "benchmark"):
        s = sub.add_parser(name)
        s.add_argument("--out", type=Path, help="New private JSON file; never overwrites")
        if name in ("preflight", "ssh-preflight"):
            s.add_argument("--cuda-image", type=pinned_image)
            s.add_argument("--target", choices=GPU_PROFILES, default="a40")
        if name == "ssh-preflight":
            s.add_argument("--host", required=True, help="Authorized SSH config alias only")
        if name == "monitor":
            s.add_argument("--samples", type=int, default=12)
            s.add_argument("--interval", type=float, default=10)
            s.add_argument("--base", default="http://127.0.0.1:8000", type=loopback_url)
            s.add_argument("--model-hash")
            s.add_argument("--policy-hash")
        if name == "benchmark":
            s.add_argument("--base", default="http://127.0.0.1:8000", type=loopback_url)
            s.add_argument("--model-hash", required=True)
            s.add_argument("--policy-hash", required=True)
            s.add_argument("--requests", type=int, default=10)
            s.add_argument("--warmup", type=int, default=2)
            s.add_argument("--max-tokens", type=int, default=128)
    args = p.parse_args()
    try:
        if args.out:
            if args.out.exists() or args.out.is_symlink():
                raise ValueError("Output must be a new file")
            args.out.parent.mkdir(parents=True, exist_ok=True)
        if args.action == "ssh-preflight":
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,100}", args.host):
                raise ValueError("Use an SSH config alias, with username and port in SSH config")
            remote = ["python3", "-", "preflight", "--target", args.target]
            if args.cuda_image:
                remote += ["--cuda-image", args.cuda_image]
            import shlex
            proc = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                "-o", "ConnectTimeout=10", "-o", "ForwardAgent=no", args.host, shlex.join(remote)],
                input=Path(__file__).read_text(), capture_output=True, text=True, timeout=240)
            # Exit 2 is a completed diagnostic with unmet prerequisites, not an
            # SSH failure. Keep that evidence and report the working transport.
            if proc.returncode not in (0, 2):
                raise ValueError("SSH preflight failed; verify trusted host key, key access, Python and host authorization")
            data = json.loads(proc.stdout)
            if data.get("schema") != SCHEMA or data.get("kind") != "preflight":
                raise ValueError("Unexpected SSH result")
            data["ssh_access"] = "PASS"
        elif args.action == "benchmark":
            if not 1 <= args.requests <= 100 or not 0 <= args.warmup <= 10 or not 1 <= args.max_tokens <= 512:
                raise ValueError("Bounds: requests 1-100, warmup 0-10, max-tokens 1-512")
            data = benchmark(args)
        elif args.action == "monitor":
            if not 1 <= args.samples <= 360 or not 1 <= args.interval <= 60:
                raise ValueError("Bounds: samples 1-360, interval 1-60 seconds")
            if bool(args.model_hash) != bool(args.policy_hash):
                raise ValueError("Supply both model and policy hashes for backend health monitoring")
            if args.model_hash:
                validate_hash(args.model_hash)
                validate_hash(args.policy_hash)
            data = envelope("monitor", samples=[], alerts=[])
            journal_fd = None
            if args.out:
                # Claim a fresh journal once; never follow or append to an
                # existing file/symlink from another collection session.
                journal = args.out.with_suffix(args.out.suffix + ".jsonl")
                journal_fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            for i in range(args.samples):
                sample = preflight()
                alerts = []
                if sample["probes"]["nvidia_smi"]["status"] != "PASS":
                    alerts.append("GPU_TELEMETRY_UNAVAILABLE")
                if sample["probes"]["docker_server"]["status"] != "PASS":
                    alerts.append("DOCKER_UNAVAILABLE")
                backend_health = "NOT_TESTED"
                if args.model_hash:
                    try:
                        health = fetch_json(args.base, "/health", os.environ.get("INFERENCE_API_KEY", ""), timeout=5)
                        backend_health = "PASS" if check_health(health, args.model_hash, args.policy_hash) else "MISMATCH"
                    except (ValueError, OSError, urllib.error.URLError):
                        backend_health = "UNAVAILABLE"
                    if backend_health != "PASS":
                        alerts.append("BACKEND_HEALTH_" + backend_health)
                for gpu in sample["gpus"]:
                    if (gpu["temperature.gpu"] or 0) >= 85:
                        alerts.append("GPU_TEMPERATURE_AT_LEAST_85C")
                    if gpu["memory.total"] and (gpu["memory.used"] or 0) / gpu["memory.total"] >= .95:
                        alerts.append("GPU_MEMORY_AT_LEAST_95_PERCENT")
                data["samples"].append({"collected_at": sample["collected_at"], "gpus": sample["gpus"],
                                        "probes": sample["probes"], "backend_health": backend_health, "alerts": alerts})
                data["alerts"] = sorted(set(data["alerts"] + alerts))
                if args.out:
                    # Incremental recovery file; final --out still uses exclusive creation.
                    with os.fdopen(os.dup(journal_fd), "a") as f:
                        f.write(json.dumps(data["samples"][-1], allow_nan=False) + "\n")
                if i + 1 < args.samples:
                    time.sleep(args.interval)
            if journal_fd is not None:
                os.close(journal_fd)
        else:
            data = preflight(args.cuda_image, args.target)
        if args.out:
            write_json(args.out, data)
        else:
            print(json.dumps(data, indent=2, allow_nan=False))
        if data["kind"] == "preflight" and data["host_prerequisites"] != "PASS":
            return 2
        if data["kind"] == "benchmark" and data["failed"]:
            return 2
        if data["kind"] == "monitor" and data["alerts"]:
            return 2
        return 0
    except (ValueError, OSError, subprocess.TimeoutExpired, urllib.error.URLError) as exc:
        # Never print exception messages from HTTP, subprocesses or secret-bearing environments.
        print(json.dumps({"status": "FAILED", "error_type": type(exc).__name__,
                          "reason": "Check command inputs, approved pins, access and backend identity; no raw logs emitted"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
