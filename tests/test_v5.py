import copy
import unittest
from computepilot.engine import execute, verify_receipt, DisabledFlopProvider

class V5Tests(unittest.TestCase):
    def test_simulated_receipt(self):
        result = execute("Summarize a new AI service")
        self.assertTrue(verify_receipt(result["receipt"], result["output"]))
        self.assertEqual(result["receipt"]["flop_settlement"], "NOT_VERIFIED")
        self.assertEqual(result["receipt"]["signature"], "NOT_SIGNED")
        self.assertTrue(result["receipt"]["audit"]["passed"])
    def test_tampering_fails(self):
        result = execute("Test task")
        self.assertFalse(verify_receipt(result["receipt"], result["output"] + " tampered"))
        altered = copy.deepcopy(result["receipt"])
        altered["provider"] = "flop"
        self.assertFalse(verify_receipt(altered, result["output"]))
    def test_flop_disabled(self):
        with self.assertRaises(RuntimeError):
            execute("Task", "flop")
    def test_live_disabled(self):
        with self.assertRaises(RuntimeError):
            execute("Task", "live")
    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            execute("  ")
        with self.assertRaises(ValueError):
            execute("x" * 2001)

if __name__ == "__main__":
    unittest.main()
