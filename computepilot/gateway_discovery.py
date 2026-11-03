"""Read the public FLOP model list; never send credentials or inference requests."""
import json
from datetime import datetime, timezone
from urllib import error, request

MODELS_URL = 'https://api.flop.network/v1/models'
USER_AGENT = 'ComputePilot/0.12 (FLOP diagnostic client)'
MAX_BYTES = 1_048_576


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError('Nonstandard JSON constant')


def parse_models(raw):
    """Validate a minimal model-list shape, not the full FLOP API contract."""
    if len(raw) > MAX_BYTES:
        raise ValueError('Oversized model list')
    payload = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object,
                         parse_constant=_invalid_constant)
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
        raise ValueError('Expected a data array')
    ids = []
    for model in payload['data']:
        if not isinstance(model, dict):
            raise ValueError('Expected model object')
        model_id = model.get('id')
        if (not isinstance(model_id, str) or not model_id.strip()
                or len(model_id) > 256 or any(ord(c) < 32 or ord(c) == 127 for c in model_id)):
            raise ValueError('Invalid model ID')
        if model_id in ids:
            raise ValueError('Duplicate model ID')
        ids.append(model_id)
    return ids


def discover_models():
    result = {
        'kind': 'gateway_discovery',
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'endpoint': MODELS_URL,
        'model_listing': 'NOT_VERIFIED',
        'model_ids': [],
        'inference': 'NOT_RUN',
        'mining': 'NOT_VERIFIED',
        'rewards': 'NOT_VERIFIED',
        'scope': 'Public model discovery only; no API key, inference or chain transaction',
    }
    req = request.Request(MODELS_URL, headers={'Accept': 'application/json', 'User-Agent': USER_AGENT}, method='GET')
    try:
        # No redirects, retries, caller-selected host, API key or paid POST path.
        with request.build_opener(NoRedirect()).open(req, timeout=10) as response:
            if response.status != 200:
                result.update(model_listing='HTTP_ERROR', http_status=response.status)
                return result
            media_type = response.headers.get_content_type()
            if media_type != 'application/json' and not media_type.endswith('+json'):
                raise ValueError('Expected JSON content type')
            ids = parse_models(response.read(MAX_BYTES + 1))
        result.update(model_listing='AVAILABLE' if ids else 'EMPTY', model_ids=ids)
    except error.HTTPError as exc:
        # Do not emit a provider error body, headers, URL or exception message.
        result.update(model_listing='HTTP_ERROR', http_status=exc.code)
    except (ValueError, UnicodeError, RecursionError):
        result['model_listing'] = 'INVALID_RESPONSE'
    except (error.URLError, OSError):
        result['model_listing'] = 'UNREACHABLE'
    return result


def main():
    result = discover_models()
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['model_listing'] == 'AVAILABLE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
