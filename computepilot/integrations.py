"""Read-only DCGM collection and offline AIPerf imports; never start a service."""
import argparse
import hashlib
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

from .miner_test import MODEL, envelope, fetch_text, loopback_url, number, stamp, write_json

# NVIDIA dcgm-exporter/etc/default-counters.csv; no hostnames or raw labels saved.
DCGM = {
    'DCGM_FI_DEV_GPU_TEMP': ('temperature_c', -50, 150),
    'DCGM_FI_DEV_POWER_USAGE': ('power_w', 0, 2000),
    'DCGM_FI_DEV_GPU_UTIL': ('utilization_pct', 0, 100),
    'DCGM_FI_DEV_FB_USED': ('memory_used_mib', 0, 1_000_000),
    'DCGM_FI_DEV_FB_FREE': ('memory_free_mib', 0, 1_000_000),
    'DCGM_FI_DEV_XID_ERRORS': ('last_xid_error', 0, 10000),
}


def parse_dcgm(text):
    rows, seen = {}, set()
    for line in text.splitlines():
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Z_0-9]+)\{(.*)\}\s+(\S+)(?:\s+\d+)?', line)
        if not match or match[1] not in DCGM:
            continue
        label = re.search(r'(?:^|,)\s*gpu="([0-9]{1,2})"\s*(?=,|$)', match[2])
        if not label:
            continue
        gpu = int(label[1])
        key, low, high = DCGM[match[1]]
        if (gpu, key) in seen:
            raise ValueError('Duplicate GPU series; use one exporter, no MIG/replica aggregation')
        seen.add((gpu, key))
        value = number(match[3])
        # DCGM sentinels (very large numbers), NaN and absent fields stay unknown.
        rows.setdefault(gpu, {'gpu_index': gpu})[key] = value if value is not None and low <= value <= high else None
    if not rows:
        raise ValueError('No supported per-GPU DCGM metrics')
    return [rows[k] for k in sorted(rows)]


def dcgm_snapshot(base):
    gpus = parse_dcgm(fetch_text(loopback_url(base), '/metrics', timeout=5))
    alerts = []
    for gpu in gpus:
        if (gpu.get('temperature_c') or 0) >= 85:
            alerts.append('GPU_TEMPERATURE_AT_LEAST_85C')
        if (gpu.get('last_xid_error') or 0) > 0:
            alerts.append('XID_ERROR_REPORTED_MAY_BE_HISTORICAL')
    return envelope('dcgm', gpus=gpus, alerts=sorted(set(alerts)),
                    missing_metrics={str(g['gpu_index']): [v[0] for v in DCGM.values() if g.get(v[0]) is None] for g in gpus},
                    scope='Single read-only loopback snapshot; missing counters are unknown, not zero')


METRICS = {'time_to_first_token': 'ms', 'request_latency': 'ms',
           'inter_token_latency': 'ms', 'output_token_throughput_per_user': 'tokens/sec/user',
           'output_sequence_length': 'tokens'}


def import_aiperf(path):
    if path.stat().st_size > 16_000_000:
        raise ValueError('AIPerf import exceeds 16 MB')
    raw = path.read_bytes()
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not records or len(records) > 10000:
        raise ValueError('Expected 1-10000 AIPerf per-request records')
    values = {k: [] for k in METRICS}
    successful, failed, ends = 0, 0, []
    for record in records:
        meta = record['metadata']
        if meta.get('benchmark_phase') != 'profiling':
            raise ValueError('Only profiling records accepted; exclude warmup')
        end = meta['request_end_ns']
        start = meta['request_start_ns']
        if type(start) is not int or type(end) is not int or not 0 < start <= end:
            raise ValueError('Invalid request timestamps')
        ends.append(end)
        if record.get('error') is not None or meta.get('was_cancelled'):
            failed += 1
            continue
        metrics = record['metrics']
        if not isinstance(metrics, dict) or not metrics:
            raise ValueError('Missing metrics on successful record')
        successful += 1
        for key, unit in METRICS.items():
            if key not in metrics:
                continue
            metric = metrics[key]
            value = number(metric.get('value'))
            if isinstance(metric.get('value'), bool) or value is None or value < 0 or metric.get('unit') != unit:
                raise ValueError('Invalid metric value or unit')
            values[key].append(value)
    summary = {k: {'unit': METRICS[k], 'samples': len(v), 'median': statistics.median(v) if v else None,
                   'p95': sorted(v)[-(-95*len(v)//100)-1] if v else None} for k, v in values.items()}
    report = envelope('aiperf', source_sha256=hashlib.sha256(raw).hexdigest(), imported_at=stamp(),
                      successful=successful, failed=failed, requested=len(records), metrics=summary,
                      model_identity='NOT_VERIFIED', scope='Unsigned external per-request metrics; import does not verify model, host, precision or policy')
    report['collected_at'] = datetime.fromtimestamp(max(ends)/1e9, timezone.utc).isoformat()
    report['evidence'] = 'EXTERNAL_OBSERVATION_UNSIGNED'
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    d = sub.add_parser('dcgm')
    d.add_argument('--base', type=loopback_url, default='http://127.0.0.1:9400')
    a = sub.add_parser('aiperf-import')
    a.add_argument('--records', type=Path, required=True, help='profile_export.jsonl, no raw request/response file')
    for parser in [d, a]:
        parser.add_argument('--out', type=Path)
    args = p.parse_args()
    try:
        result = dcgm_snapshot(args.base) if args.action == 'dcgm' else import_aiperf(args.records)
        if args.out:
            write_json(args.out, result)
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if result.get('alerts') or result.get('failed') else 0
    except (ValueError, KeyError, TypeError, IndexError, OverflowError, OSError):
        print(json.dumps({'status': 'FAILED', 'reason': 'Invalid input or unavailable service; no raw logs emitted'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
