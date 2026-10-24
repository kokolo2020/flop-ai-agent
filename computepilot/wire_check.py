"""Offline Appendix F encoding checks. No signing, signature verification or RPC.

Independent implementation of a documented subset; provenance accompanies the
unchanged FLOP Labs corpus in tests/fixtures/flop-wire-v1 (CC BY 4.0).
"""
import hashlib
import json
from pathlib import Path


def uint(value, size):
    if type(value) is not int or not 0 <= value < 1 << (8 * size):
        raise ValueError('Unsigned integer out of range')
    return value.to_bytes(size, 'little')


def fixed(value):
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError('Expected 32 bytes')
    return value


def digest(data):
    return hashlib.blake2b(data, digest_size=32).digest()


def compact(value):
    uint(value, 4)
    for bits, size, tag in [(6, 1, 0), (14, 2, 1), (30, 4, 2)]:
        if value < 1 << bits:
            return ((value << 2) | tag).to_bytes(size, 'little')
    return b'\x03' + uint(value, 4)


def decode_compact(data):
    if not data:
        raise ValueError('Truncated compact integer')
    tag = data[0] & 3
    size = [1, 2, 4, 5 + (data[0] >> 2)][tag]
    if len(data) != size or size > 5:
        raise ValueError('Truncated, trailing or overflowing compact integer')
    value = int.from_bytes(data[1:] if tag == 3 else data, 'little')
    if tag != 3:
        value >>= 2
    if compact(value) != data:
        raise ValueError('Noncanonical compact integer')
    return value


def channel_preimage(genesis, agent, miner, nonce):
    return b'FLOP/COMPUTE_CHANNEL/ID\x01' + fixed(genesis) + fixed(agent) + fixed(miner) + uint(nonce, 8)


def receipt_preimage(channel, root, aggregate_gn, payable):
    return b'FLOP/COMPUTE_CHANNEL/RECEIPT\x01' + fixed(channel) + fixed(root) + uint(aggregate_gn, 16) + uint(payable, 16)


def ids_preimage(prompt, generated):
    return b''.join(uint(len(ids), 4) + b''.join(uint(n, 4) for n in ids) for ids in [prompt, generated])


def leaf_preimage(version, fields):
    if type(version) is not int or version not in range(4):
        raise ValueError('Unknown leaf version')
    value = fixed(bytes.fromhex(fields['channel_id_hex'])) + uint(fields['turn_index'], 4)
    value += fixed(bytes.fromhex(fields['h_in_hex'])) + fixed(bytes.fromhex(fields['h_out_hex'])) + uint(int(fields['g_n']), 16)
    if version >= 2:
        value += fixed(bytes.fromhex(fields['decode_policy_hash_hex']))
    if version == 3:
        value += fixed(bytes.fromhex(fields['h_ids_hex'])) + fixed(bytes.fromhex(fields['toploc_commitment_hash_hex']))
    if version >= 1:
        value += b''.join(uint(int(fields[k]), 8) for k in ['miner_recv_ms', 'miner_done_ms', 'latency_ms'])
    return value


def merkle_root(leaves):
    level = [fixed(v) for v in leaves]
    if not level:
        return bytes(32)
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [digest(level[i] + level[i+1]) for i in range(0, len(level), 2)]
    return level[0]


def check_vectors(directory=None):
    directory = directory or Path(__file__).resolve().parents[1] / 'tests/fixtures/flop-wire-v1'
    raw = (directory / 'wire-format-v1.json').read_bytes()
    source = json.loads((directory / 'provenance.json').read_text())
    if hashlib.sha256(raw).hexdigest() != source['sha256']:
        raise ValueError('Pinned corpus SHA-256 mismatch')
    v = json.loads(raw)
    checks = []

    def equal(name, got, want):
        checks.append({'check': name, 'status': 'PASS' if got == want else 'FAIL'})

    for row in v['codec']['scale_compact_u32']:
        equal('compact encode ' + str(row['value']), compact(row['value']).hex(), row['bytes_hex'])
        equal('compact decode ' + str(row['value']), decode_compact(bytes.fromhex(row['bytes_hex'])), row['value'])
    for row in v['codec']['malformed_compact']:
        try:
            decode_compact(bytes.fromhex(row['bytes_hex']))
            rejected = False
        except ValueError:
            rejected = True
        equal('compact reject ' + row['reason'], rejected, True)
    channel = v['compute_channel_v1']
    ci = channel['channel_id']['inputs']
    cp = channel_preimage(*(bytes.fromhex(ci[k]) for k in ['genesis_hash_hex', 'agent_account_id32_hex', 'miner_account_id32_hex']), int(ci['nonce']))
    equal('channel preimage', cp.hex(), channel['channel_id']['preimage_hex'])
    equal('channel hash', digest(cp).hex(), channel['channel_id']['hash_hex'])
    for case in ['wrong_genesis_network', 'wrong_session']:
        neg = next(n for n in v['negative_cases'] if n['id'] == case)
        inputs = [bytes.fromhex(ci[k]) for k in ['genesis_hash_hex', 'agent_account_id32_hex', 'miner_account_id32_hex']]
        inputs[0 if case == 'wrong_genesis_network' else 1] = (bytes([1]) + inputs[0][1:]) if case == 'wrong_genesis_network' else bytes([0x12])*32
        changed = digest(channel_preimage(*inputs, int(ci['nonce'])))
        equal(case, changed.hex(), neg['bytes_hex'])
        equal(case + ' differs', changed != digest(cp), True)
    ri = channel['receipt']['inputs']
    rp = receipt_preimage(bytes.fromhex(ri['channel_id_hex']), bytes.fromhex(ri['final_root_hex']), int(ri['aggregate_gn']), int(ri['payable']))
    equal('receipt preimage', rp.hex(), channel['receipt']['preimage_hex'])
    for row in v['h_ids_v1']['vectors']:
        data = ids_preimage(row['prompt_ids'], row['generated_ids'])
        equal('token ids preimage ' + row['id'], data.hex(), row['preimage_hex'])
        equal('token ids hash ' + row['id'], digest(data).hex(), row['hash_hex'])
    leaves = {}
    for row in channel['leaf_versions']:
        data = leaf_preimage(row['scale_tag'], channel['leaf_inputs'])
        equal(row['version'] + ' leaf preimage', data.hex(), row['preimage_hex'])
        leaves[row['version']] = digest(data)
        equal(row['version'] + ' leaf hash', leaves[row['version']].hex(), row['hash_hex'])
    merkle = channel['merkle']
    equal('odd leaf Merkle root', merkle_root([leaves[k] for k in merkle['leaf_order']]).hex(), merkle['root_hex'])
    current = leaves['V3']
    for step in merkle['path_for_index_2']:
        sibling = bytes.fromhex(step['sibling_hex'])
        current = digest(sibling + current if step['sibling_is_left'] else current + sibling)
    equal('Merkle path', current.hex(), merkle['root_hex'])
    policy = v['decode_policy_v1']
    preimage = b'FLOP_DECODE_POLICY_HASH_V1' + bytes.fromhex(policy['scale_bytes_hex'])
    equal('policy domain', preimage.hex(), policy['hash_preimage_hex'])
    equal('policy digest', hashlib.sha256(preimage).hexdigest(), policy['sha256_hex'])
    return {'schema': 'computepilot.wire-check.v12', 'evidence': 'PROTOCOL_FIXTURE_CHECK_ONLY',
            'simulated': True, 'flop_activity': 'NOT_VERIFIED', 'mining_activation': 'NOT_PERFORMED',
            'status': 'PASS' if all(c['status'] == 'PASS' for c in checks) else 'FAIL',
            'source': source, 'checks': checks, 'not_checked': ['sr25519 signatures', 'FCC4 decoding',
            'verified-turn decoding and semantic rejection cases', 'direct rail attestations',
            'live runtime compatibility', 'TOPLOC verification', 'network acceptance or settlement']}


if __name__ == '__main__':
    result = check_vectors()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] == 'PASS' else 2)
