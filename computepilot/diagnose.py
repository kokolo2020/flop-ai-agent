"""Deterministic GPU diagnostic decisions from unsigned preflight reports.

No model inference, network calls, shell commands or automatic repairs.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .miner_test import SCHEMA as INPUT_SCHEMA, write_json

SCHEMA = 'computepilot.diagnosis.v1'
MAX_BYTES = 2_000_000


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Missing timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp needs timezone')
    return parsed


def finite(value, low, high):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def diagnose(source, now=None):
    now = now or datetime.now(timezone.utc)
    if (not isinstance(source, dict) or source.get('schema') != INPUT_SCHEMA
            or source.get('kind') != 'preflight' or source.get('simulated') is not False
            or source.get('evidence') != 'LOCAL_OBSERVATION_UNSIGNED'):
        raise ValueError('Expected unsigned non-simulated preflight schema')
    collected = timestamp(source.get('collected_at'))
    age = (now - collected).total_seconds()
    fresh = -60 <= age <= 300
    gpus, probes = source.get('gpus'), source.get('probes')
    if not isinstance(gpus, list) or len(gpus) > 64 or not isinstance(probes, dict):
        raise ValueError('Invalid inventory or probes')
    issues, unknown, observations = [], [], []

    def issue(code, evidence, recommendation):
        issues.append(dict(code=code, evidence=evidence, recommendation=recommendation,
                           cause='NOT_ESTABLISHED', repair='NOT_EXECUTED'))

    for key in ('nvidia_smi', 'docker_server'):
        probe = probes.get(key)
        status = probe.get('status') if isinstance(probe, dict) else None
        if status == 'PASS':
            continue
        if status in ('FAIL', 'MISSING', 'TIMEOUT_OR_OS_ERROR', 'INVALID_OUTPUT'):
            issue(key.upper() + '_UNAVAILABLE', {'probe_status': status},
                  'Check tool availability, service access and permissions; collect a new preflight. A failed probe alone does not identify the cause.')
        else:
            unknown.append(key)
    if not gpus:
        unknown.append('gpu_inventory')
    for index, gpu in enumerate(gpus):
        if not isinstance(gpu, dict):
            raise ValueError('Invalid GPU entry')
        name, total = gpu.get('name'), gpu.get('memory.total')
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise ValueError('Invalid GPU name')
        if not finite(total, 1, 1_000_000):
            unknown.append('gpu_%d_total_memory' % index)
        temp, used = gpu.get('temperature.gpu'), gpu.get('memory.used')
        observed = {'gpu_index': index, 'name_sha256': hashlib.sha256(name.encode()).hexdigest(),
                    'memory_total_mib': total if finite(total, 1, 1_000_000) else None}
        if finite(temp, -50, 150):
            observed['temperature_c'] = temp
            if temp >= 85:
                issue('GPU_%d_TEMPERATURE_AT_LEAST_85C' % index, {'temperature_c': temp},
                      'Inspect cooling and workload against the GPU manufacturer limits; 85 C is a diagnostic heuristic. Recheck temperature after any operator-approved correction.')
        else:
            unknown.append('gpu_%d_temperature' % index)
        if finite(total, 1, 1_000_000) and finite(used, 0, total):
            observed['memory_used_mib'] = used
            if used / total >= .95:
                issue('GPU_%d_MEMORY_AT_LEAST_95_PERCENT' % index, {'used_mib': used, 'total_mib': total},
                      'Inspect memory use and request failures. High allocation alone does not prove an out-of-memory error; review batch size and context length before changing them.')
        else:
            unknown.append('gpu_%d_used_memory' % index)
        observations.append(observed)
    state = 'STALE' if not fresh else ('NEEDS_ATTENTION' if issues else ('INCOMPLETE' if unknown else 'CHECKS_CLEAR'))
    return dict(schema=SCHEMA, source_collected_at=collected.isoformat(),
                state=state, fresh=fresh, issues=issues, unknown=unknown,
                observations=observations, evidence='LOCAL_OBSERVATION_UNSIGNED',
                root_cause='NOT_ESTABLISHED', inference='NOT_RUN', repair='NOT_EXECUTED',
                flop_activity='NOT_VERIFIED', recovery='NOT_CHECKED',
                scope='Rule-based tool layer; checks cover telemetry access, Docker access, temperature and memory only')


def compare(before, after, same_host_asserted=False, now=None):
    previous, current = diagnose(before, now), diagnose(after, now)
    current['recovery'] = 'INCONCLUSIVE'
    old_time, new_time = timestamp(before['collected_at']), timestamp(after['collected_at'])
    # This collector has no authenticated host ID. Require the operator to assert
    # same-host collection and still refuse changed/reordered GPU inventories.
    identity = lambda report: [(g['name_sha256'], g['memory_total_mib']) for g in report['observations']]
    if (not same_host_asserted or not current['fresh'] or new_time <= old_time
            or not identity(previous) or identity(previous) != identity(current)):
        return current
    old_codes = {i['code'] for i in previous['issues']}
    new_codes = {i['code'] for i in current['issues']}
    if old_codes and current['state'] == 'CHECKS_CLEAR':
        current['recovery'] = 'OBSERVED_CLEARANCE_UNSIGNED'
        current['cleared_conditions'] = sorted(old_codes)
    elif old_codes & new_codes:
        current['recovery'] = 'CONDITIONS_PERSIST'
    current['same_host'] = 'OPERATOR_ASSERTED_NOT_AUTHENTICATED'
    current['repair_effectiveness'] = 'NOT_PROVEN_BY_TWO_SNAPSHOTS'
    return current


def read_source(path):
    with path.open('rb') as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Report exceeds limit')
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--before', type=Path)
    parser.add_argument('--same-host', action='store_true', help='Operator assertion; does not authenticate host identity')
    parser.add_argument('--out', type=Path, help='New private JSON result file; never overwrites')
    args = parser.parse_args()
    try:
        after = read_source(args.report)
        result = compare(read_source(args.before), after, args.same_host) if args.before else diagnose(after)
        if args.out:
            write_json(args.out, result)
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['state'] == 'CHECKS_CLEAR' else 2
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError):
        print(json.dumps({'state': 'INVALID_INPUT', 'reason': 'Unsupported or unavailable report; no raw input emitted'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
