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
            'images':{'worker':'ghcr.io/flop-labs/flop-core/miner-worker:v0.1.237@sha256:'+'5'*64,
                      'backend':'ghcr.io/flop-labs/flop-core/miner-vllm-toploc:v0.1.237@sha256:'+'6'*64},
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

    def add_artifact(self, name):
        raw = b'NONEXECUTABLE TOPOLOGY FIXTURE\n'
        (self.root / (name + '.fixture')).write_bytes(raw)
        self.plan['artifacts'][name] = {'path':name + '.fixture', 'sha256':hashlib.sha256(raw).hexdigest()}

    def public_preview(self):
        self.plan['deployment'] = {'topology':'same-host', 'network_path':'public-preview',
                                   'session_public_host':'fixture-miner.example.com'}
        self.env['SESSION_PUBLIC_HOST'] = 'fixture-miner.example.com'
        for key, field, value in [('FLOP_RPC','rpc','wss://rpc.devnet.flop.network'),
                                  ('GHOST_MAILBOX_URL','ghost_mailbox','https://mailbox.devnet.flop.network')]:
            self.env[key] = self.plan['endpoints'][field] = value
        self.add_artifact('tls_compose')

    def split_backend(self):
        deployment = self.plan.setdefault('deployment', {'network_path':'tailnet'})
        deployment.update(topology='runpod-backend', backend_origin='https://fixturepod-8000.proxy.runpod.net')
        self.env['OPENAI_BASE_URL'] = deployment['backend_origin'] + '/v1'
        self.env.pop('MODEL_CHECKPOINT_DIR', None)
        self.plan['artifacts'].pop('backend_compose', None)
        self.add_artifact('backend_deployment')
        self.backend = {key:self.env[key] for key in ['MODEL_NAME','MODEL_HASH','TOPLOC_PRECISION',
                       'DECODE_POLICY_HASH','DECODE_POLICY','INFERENCE_API_KEY']}
        self.backend.update(MODEL_REVISION=self.plan['model']['revision'], MODEL_DIR='/opt/flop-model')

    def split_check(self):
        pin = self.write_inputs()
        path = self.root/'backend.env'
        path.write_text('\n'.join(f'{k}={v}' for k,v in self.backend.items()))
        path.chmod(0o600)
        return b.check_bundle(self.root,'operator-plan.json',pin,'miner-01.env','backend.env')

    def test_version_and_digest_required_for_both_images(self):
        for component in ['worker','backend']:
            original = self.plan['images'][component]
            for bad in [original.replace(':v0.1.237',''), original.replace(':v0.1.237',':stable'),
                        original.split('@')[0], original.replace(':v0.1.237',':sha-1234')]:
                with self.subTest(component=component, bad=bad):
                    self.env['FLOP_' + component.upper() + '_IMAGE'] = self.plan['images'][component] = bad
                    self.assertEqual(self.check()['configuration_checks'],'INCOMPLETE')
            self.env['FLOP_' + component.upper() + '_IMAGE'] = self.plan['images'][component] = original

    def test_public_preview_checks_tls_and_loopback_but_never_admits(self):
        self.public_preview()
        report = self.check()
        self.assertEqual(report['configuration_checks'],'PASS')
        self.assertEqual(report['operator_admission'],'NOT_VERIFIED')
        self.assertEqual(report['activation_gate'],'BLOCKED')
        for key, value in [('SESSION_BIND_IP','0.0.0.0'), ('SESSION_PUBLIC_HOST','another.example.com')]:
            original = self.env[key]
            self.env[key] = value
            self.assertEqual(self.check()['configuration_checks'],'INCOMPLETE')
            self.env[key] = original

    def test_public_preview_needs_tls_artifact_and_secure_endpoints(self):
        self.public_preview()
        self.plan['artifacts'].pop('tls_compose')
        self.assertEqual(self.check()['configuration_checks'],'INCOMPLETE')
        self.add_artifact('tls_compose')
        self.plan['endpoints']['rpc'] = self.env['FLOP_RPC'] = 'ws://rpc.devnet.flop.network'
        self.assertEqual(self.check()['configuration_checks'],'INCOMPLETE')

    def test_unknown_or_incomplete_deployment_never_falls_back(self):
        for bad in [None, {}, {'topology':'serverless','network_path':'tailnet'},
                    {'topology':'same-host','network_path':'public'}]:
            self.plan['deployment'] = bad
            self.assertEqual(self.check()['configuration_checks'],'INCOMPLETE')
        self.plan.pop('deployment')
        self.env['SESSION_PUBLIC_HOST'] = 'fixture.example.com'
        self.assertEqual(self.check()['configuration_checks'],'INCOMPLETE')

    def test_runpod_split_and_public_combination_pass_only_offline(self):
        for public in [False, True]:
            with self.subTest(public=public):
                if public:
                    self.public_preview()
                self.split_backend()
                report = self.split_check()
                self.assertEqual(report['configuration_checks'],'PASS')
                self.assertEqual(report['activation_gate'],'BLOCKED')
                self.assertNotIn(self.env['INFERENCE_API_KEY'],json.dumps(report))
                self.assertNotIn(self.plan['deployment']['backend_origin'],json.dumps(report))
                self.assertLessEqual(len(report['checks']),100)

    def test_runpod_requires_separate_private_env_and_matching_identity(self):
        self.split_backend()
        self.assertEqual(self.check()['configuration_checks'],'INCOMPLETE')
        for key in ['MODEL_REVISION','MODEL_HASH','INFERENCE_API_KEY','DECODE_POLICY','TOPLOC_PRECISION']:
            original = self.backend[key]
            self.backend[key] = 'WRONG_PRIVATE_VALUE'
            report = self.split_check()
            self.assertEqual(report['configuration_checks'],'INCOMPLETE')
            self.assertNotIn('WRONG_PRIVATE_VALUE',json.dumps(report))
            self.backend[key] = original
        self.split_check()
        (self.root/'backend.env').chmod(0o644)
        pin = self.write_inputs()
        report = b.check_bundle(self.root,'operator-plan.json',pin,'miner-01.env','backend.env')
        self.assertEqual(report['configuration_checks'],'INCOMPLETE')

    def test_runpod_rejects_serverless_and_unqualified_release(self):
        self.split_backend()
        for origin in ['https://api.runpod.ai/v2/fixture', 'http://fixturepod-8000.proxy.runpod.net',
                       'https://fixturepod-8000.proxy.runpod.net/health',
                       'https://fixturepod-8000.proxy.runpod.net.evil.example', 12]:
            self.plan['deployment']['backend_origin'] = origin
            self.assertEqual(self.split_check()['configuration_checks'],'INCOMPLETE')
        self.plan['deployment']['backend_origin'] = 'https://fixturepod-8000.proxy.runpod.net'
        for ref in [self.plan['images']['backend'].replace('0.1.237','0.1.236'), None, 12]:
            self.plan['images']['backend'] = ref
            self.env['FLOP_BACKEND_IMAGE'] = str(ref)
            self.assertEqual(self.split_check()['configuration_checks'],'INCOMPLETE')

    def test_public_hostname_has_no_credentials_path_port_or_placeholder(self):
        for value in ['127.0.0.1','https://miner.example.com','miner.example.com:443','miner.invalid',
                      'miner.INVALID','REPLACE.example.com','user@miner.example.com','-miner.example.com',None]:
            self.assertFalse(b.public_host(value))

    def test_same_host_does_not_read_unexpected_backend_env(self):
        pin = self.write_inputs()
        with patch.object(b,'read_file',wraps=b.read_file) as read:
            report = b.check_bundle(self.root,'operator-plan.json',pin,'miner-01.env','unrelated-private.env')
        self.assertEqual(report['configuration_checks'],'INCOMPLETE')
        self.assertNotIn('unrelated-private.env',[c.args[1] for c in read.call_args_list])

    def test_cli_split_backend_redacts_private_values(self):
        self.split_backend()
        self.split_check()
        pin = self.write_inputs()
        args = ['operator_bundle','--directory',str(self.root),'--expected-manifest-sha256',pin,
                '--env','miner-01.env','--backend-env','backend.env']
        with patch('sys.argv',args), patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(b.main(),0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['activation_gate'],'BLOCKED')
        for value in [self.env['INFERENCE_API_KEY'],self.env['SESSION_AUTH_TOKEN'],
                      self.plan['deployment']['backend_origin'],self.backend['MODEL_DIR']]:
            self.assertNotIn(value,output.getvalue())

    def test_checked_in_examples_are_incomplete(self):
        examples = Path(__file__).resolve().parents[1]/'examples'
        for name in ['operator-plan.example.json','operator-plan.runpod-public.example.json']:
            pin = hashlib.sha256((examples/name).read_bytes()).hexdigest()
            report = b.check_bundle(examples,name,pin)
            self.assertEqual(report['configuration_checks'],'INCOMPLETE')
            self.assertEqual(report['activation_gate'],'BLOCKED')


if __name__ == '__main__':
    unittest.main()
