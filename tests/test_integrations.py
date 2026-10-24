"""Synthetic adapter tests. These observations are not saved as actual results."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from computepilot import integrations as i
from computepilot import miner_test as m


class IntegrationTests(unittest.TestCase):
    def test_gpu_profiles_do_not_accept_mig_or_extra_cards(self):
        gpu = {'name': 'NVIDIA A100-SXM4-80GB', 'memory.total': 81000}
        self.assertTrue(m.hardware_matches([gpu], 'a100-80'))
        self.assertFalse(m.hardware_matches([gpu], 'a40'))
        self.assertFalse(m.hardware_matches([gpu,gpu], 'a100-80'))
        self.assertFalse(m.hardware_matches([dict(gpu,name='MIG 1g.10gb')], 'a100-80'))

    def test_dcgm_drops_labels_and_sentinels(self):
        metrics = 'DCGM_FI_DEV_GPU_TEMP{gpu="0",Hostname="PRIVATE",UUID="SECRET"} 40\nDCGM_FI_DEV_FB_FREE{gpu="0"} 9223372036854775794\nDCGM_FI_DEV_POWER_USAGE{gpu="0"} NaN'
        rows = i.parse_dcgm(metrics)
        self.assertEqual(rows, [{'gpu_index':0,'temperature_c':40,'memory_free_mib':None,'power_w':None}])
        self.assertNotIn('SECRET',json.dumps(rows))

    def test_dcgm_duplicate_gpu_series_rejected(self):
        with self.assertRaises(ValueError):
            i.parse_dcgm('DCGM_FI_DEV_GPU_TEMP{gpu="0"} 40\nDCGM_FI_DEV_GPU_TEMP{gpu="0",instance="other"} 50')

    def test_dcgm_snapshot_is_read_only_and_xid_is_not_called_new(self):
        with patch.object(i,'fetch_text',return_value='DCGM_FI_DEV_XID_ERRORS{gpu="0"} 31') as fetch:
            result = i.dcgm_snapshot('http://localhost:9400')
        self.assertIn('XID_ERROR_REPORTED_MAY_BE_HISTORICAL',result['alerts'])
        fetch.assert_called_once_with('http://localhost:9400','/metrics',timeout=5)
        self.assertEqual(result['flop_activity'],'NOT_VERIFIED')

    def test_aiperf_keeps_source_time_and_discards_payload(self):
        records = [{'metadata':{'benchmark_phase':'profiling','request_start_ns':1000000000,'request_end_ns':2000000000},'error':None,'metrics':{'time_to_first_token':{'value':12,'unit':'ms'}},'response':'SECRET'}]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'profile_export.jsonl'
            p.write_text(json.dumps(records[0])+'\n')
            result = i.import_aiperf(p)
            self.assertTrue(result['collected_at'].startswith('1970-01-01'))
            self.assertEqual(result['metrics']['time_to_first_token']['median'],12)
            self.assertEqual(result['metrics']['request_latency']['samples'],0)
            self.assertEqual(result['model_identity'],'NOT_VERIFIED')
            self.assertNotIn('SECRET',json.dumps(result))
            records[0]['metrics']['time_to_first_token']['unit'] = 'seconds'
            p.write_text(json.dumps(records[0]))
            with self.assertRaises(ValueError):
                i.import_aiperf(p)


if __name__ == '__main__':
    unittest.main()
