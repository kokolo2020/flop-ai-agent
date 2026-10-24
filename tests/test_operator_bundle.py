"""Synthetic private bundle fixtures. Never GPU, admission or accepted-work evidence."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from computepilot import operator_bundle as b


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = {
            'schema':'computepilot.operator-plan.v12','network':'devnet',
            'expected_genesis_hash':'0x'+'1'*64,
            'expected_runtime':{'spec_name':'fixture-devnet','spec_version':1,'transaction_version':1},
            'model':{'name':b.MODEL,'precision':'BF16','revision':'2'*40,'hash':'0x'+'3'*64},
            'decode_policy_hash':'0x'+'4'*64,
            'images':{'worker':'ghcr.io/flop-labs/flop-core/miner-worker@sha256:'+'5'*64,
                      'backend':'ghcr.io/flop-labs/flop-core/miner-vllm-toploc@sha256:'+'6'*64},
            'endpoints':{'rpc':'ws://fixture-operator.internal:8081','da':'http://fixture-da.internal:7001',
                         'ghost_mailbox':'http://fixture-mailbox.internal:8081'},
            'artifacts':{}}
        for label in b.ARTIFACTS:
            filename = label + '.fixture'
            raw = b'{"policy":"fixture-only"}' if label == 'decode_policy' else b'NONEXECUTABLE SYNTHETIC FIXTURE\n'
            (self.root/filename).write_bytes(raw)
            self.plan['artifacts'][label] = {'path':filename,'sha256':hashlib.sha256(raw).hexdigest()}
        self.env = {'FLOP_WORKER_IMAGE':self.plan['images']['worker'],
                    'FLOP_BACKEND_IMAGE':self.plan['images']['backend'],
                    'FLOP_RPC':self.plan['endpoints']['rpc'],'DA_URL':self.plan['endpoints']['da'],
                    'GHOST_MAILBOX_URL':self.plan['endpoints']['ghost_mailbox'],
                    'MODEL_NAME':b.MODEL,'MODEL_HASH':self.plan['model']['hash'],
                    'MODEL_PRECISION':'BF16','TOPLOC_PRECISION':'bf16',
                    'DECODE_POLICY_HASH':self.plan['decode_policy_hash'],
                    'DECODE_POLICY':"'{\"policy\":\"fixture-only\"}'",
                    'OPENAI_BASE_URL':'http://backend:8000/v1','SESSION_BIND_IP':'127.0.0.1','SESSION_HOST_PORT':'8645',
                    'OPENROUTER_MODEL_SLUG':'qwen/qwen2.5-0.5b-instruct',
                    'MINER_SIGNER_FILE':'/private/fixture/signer','MINER_ENCLAVE_KEY_FILE':'/private/fixture/enclave.seed',
                    'MODEL_CHECKPOINT_DIR':'/private/fixture/checkpoint','GHOST_KEY_FILE':'/data/fixture-ghost.json',
                    'INFERENCE_API_KEY':'a'*64,'SESSION_AUTH_TOKEN':'b'*64}

    def write_inputs(self):
        raw = json.dumps(self.plan).encode()
        (self.root/'operator-plan.json').write_bytes(raw)
        (self.root/'miner-01.env').write_text('\n'.join(f'{k}={v}' for k,v in self.env.items())+'\n')
        (self.root/'miner-01.env').chmod(0o600)
        return hashlib.sha256(raw).hexdigest()

    def check(self):
        return b.check_bundle(self.root,'operator-plan.json',self.write_inputs(),'miner-01.env')

    def test_consistency_pass_never_authenticates_or_activates(self):
        report = self.check()
        self.assertEqual(report['configuration_checks'],'PASS')
        self.assertEqual(report['operator_release_verification'],'NOT_PERFORMED')
        self.assertEqual(report['operator_admission'],'NOT_VERIFIED')
        self.assertEqual(report['network_identity'],'NOT_VERIFIED')
        self.assertEqual(report['activation_gate'],'BLOCKED')
        self.assertEqual(report['flop_activity'],'NOT_VERIFIED')
        serialized = json.dumps(report)
        for private in [self.env['INFERENCE_API_KEY'],self.env['SESSION_AUTH_TOKEN'],self.env['FLOP_RPC'],'fixture-only']:
            self.assertNotIn(private,serialized)

    def test_manifest_mismatch_stops_before_private_or_artifact_reads(self):
        self.write_inputs()
        with patch.object(b,'read_file',wraps=b.read_file) as read:
            report = b.check_bundle(self.root,'operator-plan.json','f'*64,'miner-01.env')
        self.assertEqual(report['configuration_checks'],'INCOMPLETE')
        self.assertEqual(read.call_count,1)

    def test_public_bind_mismatched_pins_and_shared_tokens_fail(self):
        for key,bad in [('SESSION_BIND_IP','0.0.0.0'),('MODEL_HASH','0x'+'e'*64),('FLOP_WORKER_IMAGE','ghcr.io/flop-labs/flop-core/miner-worker:latest'),('FLOP_RPC','ws://different.internal:8081'),('SESSION_AUTH_TOKEN','a'*64)]:
            with self.subTest(key=key):
                original = self.env[key]
                self.env[key] = bad
                self.assertEqual(self.check()['configuration_checks'],'INCOMPLETE')
                self.env[key] = original

    def test_changed_artifact_fails_even_with_matching_manifest_pin(self):
        pin = self.write_inputs()
        (self.root/'backend_compose.fixture').write_text('tampered')
        report = b.check_bundle(self.root,'operator-plan.json',pin,'miner-01.env')
        self.assertIn({'check':'artifact_backend_compose','status':'FAIL'},report['checks'])

    def test_no_env_is_incomplete_not_ready(self):
        report = b.check_bundle(self.root,'operator-plan.json',self.write_inputs())
        self.assertEqual(report['configuration_checks'],'INCOMPLETE')

    def test_env_permissions_are_checked_without_printing_values(self):
        pin = self.write_inputs()
        (self.root/'miner-01.env').chmod(0o644)
        report = b.check_bundle(self.root,'operator-plan.json',pin,'miner-01.env')
        self.assertIn({'check':'private_env_readable_and_restricted','status':'FAIL'},report['checks'])

    def test_symlinks_and_path_escape_are_rejected(self):
        (self.root/'target').write_text('private')
        (self.root/'link').symlink_to('target')
        for relative in ['../outside','/etc/passwd','link']:
            with self.subTest(relative=relative), self.assertRaises((ValueError,OSError)):
                b.read_file(self.root,relative)
        (self.root/'nested-link').symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(OSError):
            b.read_file(self.root,'nested-link/target')

    def test_env_is_not_a_shell_and_duplicates_fail(self):
        for raw in [b'A=$(touch /tmp/NEVER_EXECUTED)',b'A=`id`',b'A=${OTHER}',b'A=one\nA=two',b'export A=one',b'A="unclosed']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                b.parse_env(raw)

    def test_policy_duplicates_and_nonfinite_values_fail(self):
        for raw in ['{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}']:
            with self.assertRaises(ValueError):
                b.load_json(raw)
        self.env['DECODE_POLICY'] = "'{\"policy\":\"wrong\"}'"
        report = self.check()
        self.assertIn({'check':'env_policy_matches_pinned_json','status':'FAIL'},report['checks'])

    def test_no_assumption_that_json_sha_is_runtime_policy_hash(self):
        report = self.check()
        self.assertEqual(report['configuration_checks'],'PASS')
        self.assertEqual(report['decode_policy_hash_recomputed'],'NOT_PERFORMED')

    def test_policy_comparison_preserves_types_and_decimal_precision(self):
        self.assertFalse(b.same_json(b.load_json('{"x":true}'),b.load_json('{"x":1}')))
        self.assertFalse(b.same_json(b.load_json('{"x":1.0}'),b.load_json('{"x":1}')))
        self.assertFalse(b.same_json(b.load_json('{"x":0.12345678901234567891}'),b.load_json('{"x":0.12345678901234567892}')))
        self.assertTrue(b.same_json(b.load_json('{"a":1,"b":[false]}'),b.load_json('{"b":[false],"a":1}')))

    def test_cli_malformed_env_error_does_not_leak(self):
        pin = self.write_inputs()
        secret = 'DO_NOT_EXPOSE_THIS_PRIVATE_VALUE'
        (self.root/'miner-01.env').write_text(secret)
        with patch('sys.argv',['operator_bundle','--directory',str(self.root),'--expected-manifest-sha256',pin,'--env','miner-01.env']), patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(b.main(),2)
        self.assertNotIn(secret,output.getvalue())

    def test_runtime_placeholders_bool_and_unknown_network_fail(self):
        self.plan['expected_runtime']['spec_version'] = True
        self.plan['network'] = 'mainnet'
        self.plan['expected_genesis_hash'] = '0x'+'0'*64
        self.assertEqual(self.check()['configuration_checks'],'INCOMPLETE')


if __name__ == '__main__':
    unittest.main()
