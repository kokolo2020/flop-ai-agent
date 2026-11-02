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

    def test_fence_handling_keeps_strict_failure(self):
        answer = '```json\n{"total_cents":60}\n```'
        self.assertTrue(runner.content_json(answer,{'total_cents':60}))
        self.assertFalse(runner.exact_json(answer,{'total_cents':60}))
        for invalid in [answer+' prose', 'Here is JSON:\n'+answer,
                        '```json\n{"total_cents":59}\n```',
                        '```json\n{"total_cents":59,"total_cents":60}\n```',
                        '```json\n{"total_cents":true}\n```']:
            self.assertFalse(runner.content_json(invalid,{'total_cents':60}))

    def fixture_report(self):
        import json
        return {'schema':'computepilot.model-smoke.v1','collected_at':'2026-11-02T07:22:00Z',
                'rows':[{'case':name,'completed':True,'answer':json.dumps(expected)} for name,_,expected in runner.CASES]}

    def test_separate_scores_preserve_observation_time_and_enforce_completion(self):
        report = self.fixture_report()
        report['rows'][0]['answer'] = '```json\n'+report['rows'][0]['answer']+'\n```'
        scored = runner.score_report(report)
        self.assertEqual(scored['passed'],5)
        self.assertEqual(scored['content_passed'],6)
        self.assertEqual(scored['collected_at'],report['collected_at'])
        report['rows'][0]['completed'] = False
        self.assertEqual(runner.score_report(report)['content_passed'],5)

    def test_rescore_rejects_missing_duplicate_and_fabricated_expected_fields(self):
        report = self.fixture_report()
        report['rows'][0]['expected'] = {'gpu':'WRONG'}
        report['rows'][0]['answer'] = '{"gpu":"WRONG"}'
        self.assertEqual(runner.score_report(report)['content_passed'],5)
        report['rows'][1] = report['rows'][0]
        with self.assertRaises(ValueError):
            runner.score_report(report)
        with self.assertRaises(ValueError):
            runner.score_report({'schema':'computepilot.model-smoke.v1','rows':[]})


if __name__ == '__main__':
    unittest.main()
