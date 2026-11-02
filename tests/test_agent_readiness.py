"""Check the smoke evaluator without importing or running a model."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('agent_readiness',Path(__file__).resolve().parents[1]/'scripts/agent_readiness.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class AgentReadinessTests(unittest.TestCase):
    def test_valid_typed_json(self):
        self.assertTrue(runner.exact_json(' {"should_run": false} ',{'should_run':False}))

    def test_boolean_is_not_integer(self):
        self.assertFalse(runner.exact_json('{"should_run":0}',{'should_run':False}))

    def test_extra_fields_and_explanations_fail(self):
        for answer in ['{"should_run":false,"extra":true}','```json\n{"should_run":false}\n```',
                       '{"should_run":false} Explanation', '[false]']:
            self.assertFalse(runner.exact_json(answer,{'should_run':False}))

    def test_duplicate_keys_fail(self):
        self.assertFalse(runner.exact_json('{"should_run":true,"should_run":false}',{'should_run':False}))

    def test_invalid_missing_or_wrong_value_fails(self):
        for answer in ['', '{}','{"total_cents":61}','{"total_cents":"60"}']:
            self.assertFalse(runner.exact_json(answer,{'total_cents':60}))


if __name__ == '__main__':
    unittest.main()
