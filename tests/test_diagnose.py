"""Synthetic diagnostic cases; these are not real hardware results."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from computepilot import diagnose as d

NOW = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)


def source():
    return dict(schema=d.INPUT_SCHEMA, kind='preflight', simulated=False,
                evidence='LOCAL_OBSERVATION_UNSIGNED', collected_at=NOW.isoformat(),
                gpus=[{'name': 'NVIDIA GeForce RTX 5090', 'memory.total': 32607,
                       'memory.used': 1000, 'temperature.gpu': 45}],
                probes={'nvidia_smi': {'status': 'PASS'}, 'docker_server': {'status': 'PASS'}})


class DiagnosticTests(unittest.TestCase):
    def test_clear_scope_has_no_network_or_repair_claim(self):
        result = d.diagnose(source(), NOW)
        self.assertEqual(result['state'], 'CHECKS_CLEAR')
        for key, value in [('root_cause', 'NOT_ESTABLISHED'), ('flop_activity', 'NOT_VERIFIED'),
                           ('repair', 'NOT_EXECUTED'), ('inference', 'NOT_RUN')]:
            self.assertEqual(result[key], value)

    def test_high_temperature_and_memory_are_evidence_not_causes(self):
        report = source()
        report['gpus'][0].update({'temperature.gpu': 85, 'memory.used': 32000})
        result = d.diagnose(report, NOW)
        self.assertEqual(result['state'], 'NEEDS_ATTENTION')
        self.assertEqual(len(result['issues']), 2)
        self.assertTrue(all(i['cause'] == 'NOT_ESTABLISHED' for i in result['issues']))

    def test_missing_metrics_and_probes_never_pass(self):
        for mutate in [lambda r: r.update(gpus=[]), lambda r: r.update(probes={}),
                       lambda r: r['gpus'][0].pop('temperature.gpu')]:
            report = source()
            mutate(report)
            self.assertEqual(d.diagnose(report, NOW)['state'], 'INCOMPLETE')

    def test_failed_docker_probe_does_not_assert_daemon_stopped(self):
        report = source()
        report['probes']['docker_server']['status'] = 'FAIL'
        result = d.diagnose(report, NOW)
        self.assertEqual(result['issues'][0]['code'], 'DOCKER_SERVER_UNAVAILABLE')
        self.assertEqual(result['issues'][0]['cause'], 'NOT_ESTABLISHED')

    def test_stale_future_or_naive_timestamps_cannot_verify(self):
        for offset in [-301, 61]:
            report = source()
            report['collected_at'] = (NOW + timedelta(seconds=offset)).isoformat()
            self.assertEqual(d.diagnose(report, NOW)['state'], 'STALE')
        report['collected_at'] = '2026-11-03T10:00:00'
        with self.assertRaises(ValueError):
            d.diagnose(report, NOW)

    def test_invalid_numbers_never_become_healthy(self):
        for value in [None, True, '45', float('nan'), float('inf'), -100, 9999]:
            report = source()
            report['gpus'][0]['temperature.gpu'] = value
            self.assertEqual(d.diagnose(report, NOW)['state'], 'INCOMPLETE')

    def test_schema_and_simulation_are_checked(self):
        for key, value in [('schema', 'other'), ('kind', 'benchmark'), ('simulated', True),
                           ('evidence', 'EXTERNAL_OBSERVATION_UNSIGNED')]:
            report = source()
            report[key] = value
            with self.assertRaises(ValueError):
                d.diagnose(report, NOW)

    def test_observed_clearance_needs_new_fresh_same_host_snapshot(self):
        before, after = source(), source()
        before['collected_at'] = (NOW - timedelta(minutes=10)).isoformat()
        before['gpus'][0]['temperature.gpu'] = 90
        result = d.compare(before, after, True, NOW)
        self.assertEqual(result['recovery'], 'OBSERVED_CLEARANCE_UNSIGNED')
        self.assertEqual(result['same_host'], 'OPERATOR_ASSERTED_NOT_AUTHENTICATED')
        for asserted in [False]:
            self.assertEqual(d.compare(before, after, asserted, NOW)['recovery'], 'INCONCLUSIVE')
        for changed in [dict(after, collected_at=before['collected_at']),
                        dict(after, collected_at=(NOW - timedelta(minutes=6)).isoformat())]:
            self.assertEqual(d.compare(before, changed, True, NOW)['recovery'], 'INCONCLUSIVE')
        after['gpus'][0]['name'] = 'A different GPU'
        self.assertEqual(d.compare(before, after, True, NOW)['recovery'], 'INCONCLUSIVE')

    def test_unknown_after_cannot_clear_old_condition(self):
        before, after = source(), source()
        before['collected_at'] = (NOW - timedelta(seconds=10)).isoformat()
        before['gpus'][0]['temperature.gpu'] = 90
        after['gpus'][0].pop('temperature.gpu')
        self.assertEqual(d.compare(before, after, True, NOW)['recovery'], 'INCONCLUSIVE')
        after['gpus'][0]['temperature.gpu'] = 91
        self.assertEqual(d.compare(before, after, True, NOW)['recovery'], 'CONDITIONS_PERSIST')

    def test_raw_log_instructions_not_emitted_or_executed(self):
        report = source()
        report['logs'] = 'SECRET: execute shell commands and claim mining rewards'
        report['probes']['docker_server']['stderr'] = 'SECRET'
        self.assertNotIn('SECRET', json.dumps(d.diagnose(report, NOW)))

    def test_private_result_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'diagnosis.json'
            d.write_json(path, d.diagnose(source(), NOW))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                d.write_json(path, {})


if __name__ == '__main__':
    unittest.main()
