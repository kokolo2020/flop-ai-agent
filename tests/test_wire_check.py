"""Official synthetic protocol fixtures, never GPU/network evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from computepilot import wire_check as w


class WireChecks(unittest.TestCase):
    def test_pinned_official_subset(self):
        report = w.check_vectors()
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(len(report['checks']), 45)
        self.assertTrue(report['simulated'])
        self.assertEqual(report['flop_activity'], 'NOT_VERIFIED')
        self.assertIn('sr25519 signatures', report['not_checked'])

    def test_u128_exact_and_overflow_rejection(self):
        self.assertEqual(w.uint(2**128-1, 16), bytes([255])*16)
        for value in [-1, 2**128, True, 1.5]:
            with self.assertRaises(ValueError):
                w.uint(value, 16)

    def test_receipt_domain_width_and_bounds(self):
        encoded = w.receipt_preimage(bytes(32), bytes(32), 2**128-1, 0)
        self.assertTrue(encoded.startswith(b'FLOP/COMPUTE_CHANNEL/RECEIPT\x01'))
        with self.assertRaises(ValueError):
            w.receipt_preimage(bytes(31), bytes(32), 1, 1)
        with self.assertRaises(ValueError):
            w.receipt_preimage(bytes(32), bytes(32), 2**128, 1)

    def test_pin_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'provenance.json').write_text(json.dumps({'sha256': '0'*64}))
            (path/'wire-format-v1.json').write_text('{}')
            with self.assertRaises(ValueError):
                w.check_vectors(path)

    def test_compact_rejects_trailing_bytes(self):
        with self.assertRaises(ValueError):
            w.decode_compact(b'\x00\x00')

    def test_merkle_order_matters(self):
        self.assertNotEqual(w.merkle_root([b'a'*32,b'b'*32]), w.merkle_root([b'b'*32,b'a'*32]))


if __name__ == '__main__':
    unittest.main()
