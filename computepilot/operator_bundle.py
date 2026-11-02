"""Offline FLOP bundle consistency checks. Never source env, run Compose or sign.

The preparation manifest is ComputePilot's format, not an official FLOP release
receipt. Matching supplied pins does not establish their authenticity or admission.
"""
import argparse
import hashlib
import json
import os
import re
import stat
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from .miner_test import MODEL, envelope, write_json

ARTIFACTS = ('worker_compose', 'backend_compose', 'env_template', 'decode_policy', 'release_receipt')
HASH = re.compile(r'0x[0-9a-fA-F]{64}')
SHA = re.compile(r'[0-9a-f]{64}')
SECRET_FIELDS = ('INFERENCE_API_KEY', 'SESSION_AUTH_TOKEN')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def load_json(raw):
    def invalid_constant(_):
        raise ValueError('Nonfinite JSON value')
    try:
        return json.loads(raw, object_pairs_hook=unique_object, parse_constant=invalid_constant, parse_float=Decimal)
    except InvalidOperation:
        raise ValueError('Invalid JSON decimal') from None


def same_json(left, right):
    """Preserve JSON types and exact decimal values; Python True == 1 is unsafe."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same_json(left[k],right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same_json(a,b) for a,b in zip(left,right))
    return left == right


def read_file(root, relative, private=False):
    """Bounded regular-file reads within the explicitly selected directory."""
    if not isinstance(relative, str) or '\\' in relative:
        raise ValueError('Invalid bundle path')
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or not parts.parts:
        raise ValueError('Bundle paths must stay relative')
    # Open every path component relative to a held directory descriptor. This
    # also avoids symlink swaps between an is_symlink check and the final read.
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts.parts[:-1]:
            next_dir = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = next_dir
        fd = os.open(parts.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 2_000_000:
                raise ValueError('Expected bounded regular file')
            if private and stat.S_IMODE(info.st_mode) & 0o077:
                raise PermissionError('Private env must deny group and other access')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                raw = stream.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError('File exceeds size limit')
            return raw
        finally:
            os.close(fd)
    finally:
        os.close(directory)


def parse_env(raw):
    """Strict single-line subset, without shell execution or interpolation."""
    result = {}
    for line in raw.decode('utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Z][A-Z0-9_]*)\s*=\s*(.*)', line)
        if not match or match[1] in result:
            raise ValueError('Unsupported or duplicate env assignment')
        value = match[2]
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError('Unbalanced env quoting')
            value = value[1:-1]
        # Shell/Compose expansions require review; never evaluate them here.
        if '$' in value or '`' in value or '\x00' in value or '\\' in value:
            raise ValueError('Env interpolation or escaping requires review')
        result[match[1]] = value
    return result


def image_ref(value, component):
    return isinstance(value, str) and bool(re.fullmatch(
        r'ghcr\.io/flop-labs/flop-core/' + component + r':v[0-9]+\.[0-9]+\.[0-9]+@sha256:[0-9a-f]{64}', value))


def runpod_origin(value):
    """Only the documented authenticated Pod proxy, never serverless or a path."""
    if not endpoint(value, ('https',)):
        return False
    url = urlsplit(value)
    return (bool(re.fullmatch(r'[a-z0-9]+-8000\.proxy\.runpod\.net', url.hostname))
            and url.port in (None, 443) and url.path == '')


def public_host(value):
    if not isinstance(value, str) or len(value) > 253:
        return False
    labels = value.split('.')
    return (len(labels) >= 2 and not value.lower().endswith('.invalid') and 'replace' not in value.lower()
            and bool(re.fullmatch(r'[A-Za-z]{2,63}', labels[-1]))
            and all(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label) for label in labels))


def absolute_path(value):
    return isinstance(value, str) and value.startswith('/') and '..' not in PurePosixPath(value).parts and '\x00' not in value and '\\' not in value


def endpoint(value, schemes):
    if not isinstance(value, str):
        return False
    try:
        url = urlsplit(value)
        _ = url.port  # Validate the port without connecting anywhere.
        return (url.scheme in schemes and bool(url.hostname) and
                not url.hostname.lower().endswith('.invalid') and
                'replace' not in value.lower() and not any(c.isspace() for c in value) and
                not url.username and not url.password and not url.query and not url.fragment)
    except ValueError:
        return False


def check_bundle(root, manifest_name, expected_manifest_sha256, env_name=None, backend_env_name=None):
    checks = []

    def add(check, good, missing=False):
        checks.append({'check': check, 'status': 'MISSING' if missing else 'PASS' if good else 'FAIL'})

    def report():
        passed = bool(checks) and all(c['status'] == 'PASS' for c in checks)
        return envelope('bundle', configuration_checks='PASS' if passed else 'INCOMPLETE',
                        checks=checks, operator_release_verification='NOT_PERFORMED',
                        network_identity='NOT_VERIFIED', operator_admission='NOT_VERIFIED',
                        decode_policy_hash_recomputed='NOT_PERFORMED', activation_gate='BLOCKED',
                        scope='Offline consistency only; no authenticity, Compose topology, network or runtime verification')

    if not isinstance(expected_manifest_sha256, str) or not SHA.fullmatch(expected_manifest_sha256) or int(expected_manifest_sha256,16) == 0:
        add('manifest_pin_supplied', False)
        return report()
    root = Path(root).resolve(strict=True)
    try:
        raw = read_file(root, manifest_name)
        if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
            add('manifest_matches_supplied_pin', False)
            return report()  # Do not open env/artifacts after a pin mismatch.
        add('manifest_matches_supplied_pin', True)
        plan = load_json(raw)
        if not isinstance(plan, dict) or plan.get('schema') != 'computepilot.operator-plan.v12':
            raise ValueError('Unsupported preparation manifest')
    except FileNotFoundError:
        add('preparation_manifest', False, missing=True)
        return report()
    except (OSError, ValueError, TypeError):
        add('preparation_manifest', False)
        return report()
    add('network_is_devnet', plan.get('network') == 'devnet')
    # Existing V12 manifests describe the original same-host/tailnet topology.
    deployment = plan.get('deployment', {'topology': 'same-host', 'network_path': 'tailnet'})
    if not isinstance(deployment, dict):
        deployment = {}
    topology, network_path = deployment.get('topology'), deployment.get('network_path')
    add('deployment_topology', topology in ('same-host', 'runpod-backend'))
    add('deployment_network_path', network_path in ('tailnet', 'public-preview'))
    if topology not in ('same-host', 'runpod-backend') or network_path not in ('tailnet', 'public-preview'):
        return report()
    split = topology == 'runpod-backend'
    if split:
        add('runpod_backend_origin', runpod_origin(deployment.get('backend_origin')))
    if network_path == 'public-preview':
        add('public_session_hostname', public_host(deployment.get('session_public_host')))
    genesis = plan.get('expected_genesis_hash')
    add('expected_genesis_supplied', isinstance(genesis, str) and bool(HASH.fullmatch(genesis)) and int(genesis[2:],16) != 0)
    runtime = plan.get('expected_runtime', {})
    runtime_ok = isinstance(runtime, dict) and isinstance(runtime.get('spec_name'), str) and bool(runtime['spec_name']) and 'replace' not in runtime['spec_name'].lower()
    add('expected_runtime_supplied', runtime_ok and all(type(runtime.get(k)) is int and 0 <= runtime[k] <= 0xffffffff for k in ['spec_version','transaction_version']))
    model = plan.get('model', {})
    if not isinstance(model, dict):
        model = {}
    add('documented_model', model.get('name') == MODEL and model.get('precision') == 'BF16')
    revision = model.get('revision')
    add('checkpoint_revision_pinned', isinstance(revision, str) and bool(re.fullmatch(r'[0-9a-f]{40}',revision)) and int(revision,16) != 0)
    for label, value in [('model_hash_supplied',model.get('hash')),('policy_hash_supplied',plan.get('decode_policy_hash'))]:
        add(label, isinstance(value,str) and bool(HASH.fullmatch(value)) and int(value[2:],16) != 0)
    images = plan.get('images', {})
    if not isinstance(images, dict):
        images = {}
    add('worker_image_digest', image_ref(images.get('worker'),'miner-worker'))
    add('backend_image_digest', image_ref(images.get('backend'),'miner-vllm-toploc'))
    if split:
        backend_ref = images.get('backend')
        match = re.search(r':v([0-9]+)\.([0-9]+)\.([0-9]+)@', backend_ref) if isinstance(backend_ref, str) else None
        add('runpod_backend_download_release', bool(match) and tuple(map(int, match.groups())) >= (0, 1, 237))
    endpoints = plan.get('endpoints', {})
    if not isinstance(endpoints, dict):
        endpoints = {}
    for label, schemes in [('rpc',('ws','wss')),('da',('http','https')),('ghost_mailbox',('http','https'))]:
        add('operator_' + label + '_endpoint_shape', endpoint(endpoints.get(label),schemes))
    if network_path == 'public-preview':
        add('public_rpc_uses_tls', endpoint(endpoints.get('rpc'), ('wss',)))
        add('public_mailbox_uses_tls', endpoint(endpoints.get('ghost_mailbox'), ('https',)))
    artifacts = plan.get('artifacts', {})
    if not isinstance(artifacts, dict):
        artifacts = {}
    policy = None
    required_artifacts = tuple(a for a in ARTIFACTS if not (split and a == 'backend_compose'))
    if split:
        required_artifacts += ('backend_deployment',)
    if network_path == 'public-preview':
        required_artifacts += ('tls_compose',)
    for label in required_artifacts:
        item = artifacts.get(label, {})
        try:
            if not isinstance(item, dict) or not isinstance(item.get('sha256'), str) or not SHA.fullmatch(item['sha256']):
                raise ValueError('Artifact pin required')
            data = read_file(root,item.get('path'))
            matches = hashlib.sha256(data).hexdigest() == item['sha256']
            add('artifact_' + label, matches)
            if label == 'decode_policy' and matches:
                policy = load_json(data)
                if not isinstance(policy, dict) or not policy:
                    raise ValueError('Expected policy object')
        except FileNotFoundError:
            add('artifact_' + label, False, missing=True)
        except (OSError, ValueError, TypeError):
            add('artifact_' + label + '_readable', False)
    if not env_name:
        add('private_env_checked', False, missing=True)
        return report()
    try:
        env = parse_env(read_file(root, env_name, private=True))
        add('private_env_readable_and_restricted', True)
    except FileNotFoundError:
        add('private_env_readable_and_restricted', False, missing=True)
        return report()
    except (OSError, ValueError, TypeError):
        add('private_env_readable_and_restricted', False)
        return report()
    expected = {'FLOP_WORKER_IMAGE':images.get('worker'),'FLOP_BACKEND_IMAGE':images.get('backend'),
                'MODEL_NAME':MODEL,'MODEL_HASH':model.get('hash'),'MODEL_PRECISION':'BF16',
                'TOPLOC_PRECISION':'bf16','DECODE_POLICY_HASH':plan.get('decode_policy_hash'),
                'OPENAI_BASE_URL':'http://backend:8000/v1','SESSION_BIND_IP':'127.0.0.1',
                'SESSION_HOST_PORT':'8645','OPENROUTER_MODEL_SLUG':'qwen/qwen2.5-0.5b-instruct'}
    if split:
        origin = deployment.get('backend_origin')
        expected['OPENAI_BASE_URL'] = origin + '/v1' if isinstance(origin, str) else None
    if network_path == 'public-preview':
        expected['SESSION_PUBLIC_HOST'] = deployment.get('session_public_host')
    else:
        add('tailnet_has_no_public_session_host', not env.get('SESSION_PUBLIC_HOST'))
    for key, value in expected.items():
        add('env_' + key, bool(value) and env.get(key) == value)
    for key, label in [('FLOP_RPC','rpc'),('DA_URL','da'),('GHOST_MAILBOX_URL','ghost_mailbox')]:
        add('env_' + key + '_matches_operator', bool(endpoints.get(label)) and env.get(key) == endpoints[label])
    paths = ['MINER_SIGNER_FILE','MINER_ENCLAVE_KEY_FILE','GHOST_KEY_FILE']
    if not split:
        paths.append('MODEL_CHECKPOINT_DIR')
    for key in paths:
        add('env_' + key + '_path', absolute_path(env.get(key)))
    for key in SECRET_FIELDS:
        value = env.get(key, '')
        add('env_' + key + '_present', bool(re.fullmatch(r'[0-9a-fA-F]{64}',value)))
    add('distinct_private_tokens', bool(env.get(SECRET_FIELDS[0])) and env.get(SECRET_FIELDS[0]) != env.get(SECRET_FIELDS[1]))
    # Do not hash raw JSON as if it were the runtime's SCALE decode-policy hash.
    try:
        add('env_policy_matches_pinned_json', policy is not None and same_json(load_json(env.get('DECODE_POLICY','')),policy))
    except (ValueError, TypeError):
        add('env_policy_matches_pinned_json', False)
    if split:
        if not backend_env_name:
            add('private_backend_env_checked', False, missing=True)
            return report()
        try:
            backend = parse_env(read_file(root, backend_env_name, private=True))
            add('private_backend_env_readable_and_restricted', True)
        except FileNotFoundError:
            add('private_backend_env_readable_and_restricted', False, missing=True)
            return report()
        except (OSError, ValueError, TypeError):
            add('private_backend_env_readable_and_restricted', False)
            return report()
        for key, value in {'MODEL_NAME': MODEL, 'MODEL_HASH': model.get('hash'),
                           'MODEL_REVISION': revision, 'TOPLOC_PRECISION': 'bf16',
                           'DECODE_POLICY_HASH': plan.get('decode_policy_hash')}.items():
            add('backend_' + key, bool(value) and backend.get(key) == value)
        add('backend_MODEL_DIR_path', absolute_path(backend.get('MODEL_DIR')))
        add('backend_private_token_matches_worker', bool(env.get('INFERENCE_API_KEY')) and
            backend.get('INFERENCE_API_KEY') == env.get('INFERENCE_API_KEY'))
        try:
            add('backend_policy_matches_pinned_json', policy is not None and same_json(load_json(backend.get('DECODE_POLICY','')), policy))
        except (ValueError, TypeError):
            add('backend_policy_matches_pinned_json', False)
    elif backend_env_name:
        add('backend_env_only_for_split_topology', False)
    return report()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--manifest', default='operator-plan.json', help='Relative to the selected bundle directory')
    parser.add_argument('--expected-manifest-sha256', required=True, help='Pin confirmed separately with the trusted operator')
    parser.add_argument('--env', help='Private env path relative to bundle directory; read only on the host')
    parser.add_argument('--backend-env', help='Private RunPod backend env path relative to bundle directory')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        result = check_bundle(args.directory,args.manifest,args.expected_manifest_sha256,args.env,args.backend_env)
        if args.out:
            write_json(args.out,result)
        else:
            print(json.dumps(result,indent=2,allow_nan=False))
        return 0 if result['configuration_checks'] == 'PASS' else 2
    except (OSError, ValueError, TypeError, RecursionError):
        print(json.dumps({'status':'FAILED','reason':'Bundle input or output unavailable; no raw values emitted'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
