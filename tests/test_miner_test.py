"""Synthetic protocol/unit fixtures only. No fixture is GPU or FLOP evidence."""
import argparse
import io
import json
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from computepilot import miner_test as m


class MinerTestSafety(unittest.TestCase):
    def test_nonfinite_telemetry_is_unknown(self):
        self.assertIsNone(m.number('NaN'))
        self.assertIsNone(m.number('[N/A]'))

    def test_missing_gpu_and_docker_never_pass(self):
        with patch.object(m, 'command', return_value=({'status': 'MISSING'}, '')):
            result = m.preflight()
        self.assertEqual(result['host_prerequisites'], 'INCOMPLETE')
        self.assertEqual(result['flop_activity'], 'NOT_VERIFIED')
        self.assertFalse(result['simulated'])  # A real observation of unavailable tools.

    def test_container_inventory_mismatch_blocks_readiness(self):
        def cmd(argv, **kw):
            raw = ''
            if argv[0] == 'nvidia-smi':
                raw = 'NVIDIA A40, 46068, 0, 0, 30, 40, 550.1\n'
            if argv[:2] == ['docker', 'run']:
                raw = 'NVIDIA T4, 15360\n'
            if argv[:2] == ['docker', 'info']:
                raw = '{"nvidia":{}}'
            return {'status': 'PASS'}, raw
        with patch.object(m, 'command', side_effect=cmd), patch.object(m.platform, 'system', return_value='Linux'), patch.object(m.platform, 'machine', return_value='x86_64'):
            result = m.preflight('nvidia/cuda@sha256:' + 'a'*64)
        self.assertEqual(result['target_a40_hardware'], 'PASS')
        self.assertEqual(result['host_prerequisites'], 'INCOMPLETE')

    def test_public_urls_and_mutable_images_rejected(self):
        for url in ['https://example.com', 'http://127.0.0.1.evil.test', 'http://secret@localhost', 'http://localhost/?token=x']:
            with self.assertRaises(ValueError):
                m.loopback_url(url)
        with self.assertRaises(ValueError):
            m.pinned_image('nvidia/cuda:latest')

    def test_health_must_bind_all_identity_fields(self):
        health = {'model_identity': 'measured', 'model_hash': 'h', 'precision': 'BF16', 'decode_policy_hash': 'p'}
        self.assertTrue(m.check_health(health, 'h', 'p'))
        for field in health:
            changed = dict(health)
            changed[field] = 'wrong'
            self.assertFalse(m.check_health(changed, 'h', 'p'))

    def test_benchmark_measures_without_claiming_network_activity(self):
        args = argparse.Namespace(base='http://127.0.0.1:8000', model_hash='0x'+'a'*64,
            policy_hash='0x'+'b'*64, warmup=1, requests=2, max_tokens=128)
        health = {'model_identity': 'measured', 'model_hash': args.model_hash,
                  'precision': 'BF16', 'decode_policy_hash': args.policy_hash}
        result = {'model': m.MODEL, 'choices': [{'message': {'content': 'fixture output'}}], 'usage': {'completion_tokens': 10}}
        with patch.dict(m.os.environ, {'INFERENCE_API_KEY': 'TEST_ONLY_SECRET'}), patch.object(m, 'fetch_json', side_effect=[health, result, result, result]), patch.object(m.time, 'perf_counter', side_effect=[0,1,2,3,4,5]):
            report = m.benchmark(args)
        self.assertEqual(report['successful'], 2)
        self.assertEqual(report['median_e2e_ms'], 1000)
        self.assertEqual(report['output_tokens_per_e2e_second'], 10)
        self.assertEqual(report['flop_activity'], 'NOT_VERIFIED')
        self.assertNotIn('TEST_ONLY_SECRET', json.dumps(report))
        self.assertNotIn('fixture output', json.dumps(report))

    def test_existing_evidence_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'result.json'
            m.write_json(path, {'first': True})
            with self.assertRaises(FileExistsError):
                m.write_json(path, {'first': False})
            self.assertEqual(json.loads(path.read_text()), {'first': True})

    def test_ssh_completed_incomplete_report_preserves_transport_evidence(self):
        report = m.envelope('preflight',host_prerequisites='INCOMPLETE')
        proc = subprocess.CompletedProcess([], 2, stdout=json.dumps(report), stderr='')
        with patch.object(m.sys,'argv',['miner_test','ssh-preflight','--host','authorized-fixture']), patch.object(m.subprocess,'run',return_value=proc) as run, patch.object(m.sys,'stdout',new_callable=io.StringIO) as output:
            code = m.main()
        self.assertEqual(code,2)
        self.assertEqual(json.loads(output.getvalue())['ssh_access'],'PASS')
        self.assertIn('StrictHostKeyChecking=yes',run.call_args.args[0])

    def test_monitor_refuses_existing_journal_before_probes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'monitor.json'
            path.with_suffix('.json.jsonl').write_text('previous evidence\n')
            with patch.object(m.sys,'argv',['miner_test','monitor','--samples','1','--out',str(path)]), patch.object(m,'preflight') as probe, patch.object(m.sys,'stdout',new_callable=io.StringIO):
                self.assertEqual(m.main(),1)
                probe.assert_not_called()
            self.assertEqual(path.with_suffix('.json.jsonl').read_text(),'previous evidence\n')


if __name__ == '__main__':
    unittest.main()
