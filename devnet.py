"""Read-only FLOP devnet helper.

Only GET requests to the public devnet API. No keys, no signing, no spending,
no airdrop points. Devnet has no rewards; this just checks the network is up and
which models miners currently serve, so the agent can be wired to it later.

Paid inference sessions (on-chain session request + settlement) are NOT
implemented: the public docs do not yet give a verified call sequence.
"""
import json
import os
import urllib.error
import urllib.request

API_BASE = os.environ.get('FLOP_API_URL', 'https://api.flop.network')
TIMEOUT = 15


def _get(path):
    req = urllib.request.Request(API_BASE + path, headers={'Accept': 'application/json', 'User-Agent': 'flop-ai-agent/devnet-readonly'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Devnet API returned HTTP {e.code} for {path}') from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f'Devnet API unreachable: {e}') from e


def models():
    """Return a trimmed list of models currently served on devnet."""
    data = _get('/v1/models')
    items = data.get('data', data if isinstance(data, list) else [])
    out = []
    for m in items:
        out.append({
            'id': m.get('id'),
            'name': m.get('name'),
            'context_length': m.get('context_length'),
            'pricing': m.get('pricing'),
        })
    return {'network': 'devnet', 'api': API_BASE, 'read_only': True, 'rewards': False, 'models': out}
