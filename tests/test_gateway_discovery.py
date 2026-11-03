"""Offline fixtures only; no real gateway or inference request is made."""
import json
import unittest
from email.message import Message
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib import error

from computepilot import gateway_discovery as g


class GatewayTests(unittest.TestCase):
    def run_response(self, raw, content_type='application/json', status=200):
        response = MagicMock()
        response.status = status
        response.headers = Message()
        response.headers['Content-Type'] = content_type
        response.read.return_value = raw
        response.__enter__.return_value = response
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(g.request, 'build_opener', return_value=opener):
            result = g.discover_models()
        return result, opener, response

    def test_listing_does_not_claim_inference_or_send_credentials(self):
        result, opener, response = self.run_response(b'{"data":[{"id":"qwen/test","extra":"ignored"}]}')
        self.assertEqual(result['model_listing'], 'AVAILABLE')
        self.assertEqual(result['model_ids'], ['qwen/test'])
        self.assertEqual(result['inference'], 'NOT_RUN')
        self.assertEqual(result['mining'], 'NOT_VERIFIED')
        self.assertEqual(result['rewards'], 'NOT_VERIFIED')
        req = opener.open.call_args.args[0]
        self.assertEqual(req.full_url, g.MODELS_URL)
        self.assertEqual(req.get_method(), 'GET')
        self.assertIsNone(req.data)
        self.assertFalse(req.has_header('Authorization'))
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(opener.open.call_args.kwargs, {'timeout': 10})
        response.read.assert_called_once_with(g.MAX_BYTES + 1)

    def test_empty_listing_is_not_available(self):
        result, _, _ = self.run_response(b'{"data":[]}')
        self.assertEqual(result['model_listing'], 'EMPTY')

    def test_malformed_or_ambiguous_payload_rejected(self):
        invalid = [b'no JSON', b'[]', b'{"data":{}}', b'{"data":[null]}',
                   b'{"data":[{"id":true}]}', b'{"data":[{"id":" "}]}',
                   b'{"data":[{"id":"x"},{"id":"x"}]}',
                   b'{"data":[],"data":[{"id":"x"}]}',
                   b'{"data":[],"x":NaN}', b'{"data":[{"id":"a\\nb"}]}',
                   b'\xff', b'x' * (g.MAX_BYTES + 1)]
        for raw in invalid:
            with self.subTest(raw=raw[:40]):
                result, _, _ = self.run_response(raw)
                self.assertEqual(result['model_listing'], 'INVALID_RESPONSE')

    def test_html_and_non_200_response_are_not_listings(self):
        result, _, _ = self.run_response(b'{"data":[]}', 'text/html')
        self.assertEqual(result['model_listing'], 'INVALID_RESPONSE')
        result, _, response = self.run_response(b'PRIVATE', status=202)
        self.assertEqual(result['model_listing'], 'HTTP_ERROR')
        response.read.assert_not_called()

    def test_http_error_is_sanitized_and_not_retried(self):
        for status in [301, 401, 403, 429, 503]:
            with self.subTest(status=status):
                opener = MagicMock()
                opener.open.side_effect = error.HTTPError(g.MODELS_URL, status, 'PRIVATE', {}, BytesIO(b'PRIVATE'))
                with patch.object(g.request, 'build_opener', return_value=opener):
                    result = g.discover_models()
                self.assertEqual(result['http_status'], status)
                self.assertEqual(result['model_listing'], 'HTTP_ERROR')
                self.assertNotIn('PRIVATE', json.dumps(result))
                self.assertEqual(opener.open.call_count, 1)

    def test_network_failure_is_not_protocol_failure(self):
        for exc in [error.URLError('PRIVATE'), TimeoutError('PRIVATE')]:
            opener = MagicMock()
            opener.open.side_effect = exc
            with patch.object(g.request, 'build_opener', return_value=opener):
                result = g.discover_models()
            self.assertEqual(result['model_listing'], 'UNREACHABLE')
            self.assertNotIn('PRIVATE', json.dumps(result))

    def test_redirect_refused_and_cli_exit_status(self):
        self.assertIsNone(g.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.invalid'))
        for state, code in [('AVAILABLE', 0), ('EMPTY', 2), ('UNREACHABLE', 2)]:
            with patch.object(g, 'discover_models', return_value={'model_listing': state}), patch('builtins.print'):
                self.assertEqual(g.main(), code)


if __name__ == '__main__':
    unittest.main()
