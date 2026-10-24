"""Offline-first inference, deterministic auditing and tamper-evident receipts."""
import hashlib
import re
import uuid
from datetime import datetime, timezone
from .receipts import SCHEMA, canonical, digest, seal, verify_receipt

def now():
    return datetime.now(timezone.utc).isoformat()

class SimulationProvider:
    name = "simulation"
    def infer(self, task):
        return {"output": "[SIMULATED ONLY] No model inference performed for: " + task, "usage": None, "provider_receipt": None}

class DisabledFlopProvider:
    name = "flop"
    def infer(self, task):
        raise RuntimeError("FLOP adapter disabled: official inference endpoint and settlement are not configured")

class DisabledLiveProvider:
    name = "live"
    def infer(self, task):
        raise RuntimeError("Live inference disabled: no provider credentials or server-side adapter configured")

PROVIDERS = {"simulation": SimulationProvider(), "flop": DisabledFlopProvider(), "live": DisabledLiveProvider()}

def audit(task, output, mode):
    checks = {
        "nonempty": bool(output.strip()),
        "max_output_chars": len(output) <= 50000,
        "no_fake_flop_settlement": not bool(re.search(r"FLOP (settled|payment confirmed|reward earned)", output, re.I)),
        "simulation_disclosed": mode != "simulation" or output.startswith("[SIMULATED ONLY]"),
    }
    return {"checks": checks, "passed": all(checks.values()), "independent_model_review": "NOT_RUN", "factual_accuracy": "NOT_VERIFIED"}

def execute(task, mode="simulation"):
    if not isinstance(task, str) or not task.strip() or len(task) > 2000:
        raise ValueError("Task must contain 1-2000 characters")
    if mode not in PROVIDERS:
        raise ValueError("Unknown provider mode")
    result = PROVIDERS[mode].infer(task.strip())
    report = audit(task, result["output"], mode)
    record = {
        "schema": SCHEMA, "job_id": str(uuid.uuid4()), "created_at": now(),
        "task_sha256": hashlib.sha256(task.strip().encode("utf-8")).hexdigest(),
        "output_sha256": hashlib.sha256(result["output"].encode("utf-8")).hexdigest(),
        "provider": mode, "provider_usage": result["usage"],
        "provider_receipt": result["provider_receipt"],
        "audit": report, "execution": "SIMULATED" if mode == "simulation" else "LIVE",
        "flop_settlement": "NOT_VERIFIED", "signature": "NOT_SIGNED",
    }
    return {"task": task.strip(), "output": result["output"], "receipt": seal(record)}
