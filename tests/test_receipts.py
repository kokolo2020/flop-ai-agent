"""Shared JS/Python contract tests; every input is synthetic, no network calls."""
import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from computepilot.receipts import canonical, digest, seal, verify_receipt
from computepilot.engine import execute

ROOT=Path(__file__).resolve().parents[1]


class ReceiptContract(unittest.TestCase):
    def test_shared_vectors(self):
        fixtures=json.loads((ROOT/'tests/fixtures/receipt-contract.json').read_text())
        for vector in fixtures['vectors']:
            with self.subTest(vector=vector['id']):
                self.assertEqual(canonical(vector['value']),vector['canonical'])
                self.assertEqual(digest(vector['value']),vector['sha256'])

    def test_browser_and_python_receipts_verify_both_directions(self):
        job=execute('ภาษาไทย and emoji 😀 contract fixture')
        body={k:v for k,v in job['receipt'].items() if k!='record_sha256'}
        requests=[{'action':'verify','receipt':job['receipt'],'output':job['output']},{'action':'seal','body':body}]
        result=json.loads(subprocess.check_output(['node','tests/helpers/receipt_bridge.cjs'],input=json.dumps(requests),text=True,cwd=ROOT))
        self.assertTrue(result[0])
        self.assertEqual(result[1],job['receipt'])
        self.assertTrue(verify_receipt(result[1],job['output']))
        self.assertFalse(verify_receipt(result[1],job['output']+' tampered'))

    def test_legacy_browser_and_python_receipts_still_match(self):
        output='Synthetic legacy fixture'
        body={'schema':'computepilot.receipt.v5','z':1,'output_sha256':hashlib.sha256(output.encode()).hexdigest(),'a':2}
        ordered_hash=hashlib.sha256(json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        receipts=[{**body,'record_sha256':ordered_hash},{**body,'record_sha256':digest(body)}]
        self.assertTrue(all(verify_receipt(r,output) for r in receipts))
        requests=[{'action':'verify','receipt':r,'output':output} for r in receipts]
        result=json.loads(subprocess.check_output(['node','tests/helpers/receipt_bridge.cjs'],input=json.dumps(requests),text=True,cwd=ROOT))
        self.assertEqual(result,[True,True])

    def test_nonportable_numbers_and_unicode_are_rejected(self):
        for value in [1.0,0.5,float('nan'),float('inf'),2**53,{'bad':'\ud800'},{1:'nonstring key'}]:
            with self.subTest(value=repr(value)),self.assertRaises(ValueError):
                canonical(value)
        cyclic=[]
        cyclic.append(cyclic)
        with self.assertRaises(ValueError):canonical(cyclic)

    def test_new_format_cannot_downgrade_or_use_unknown_encoding(self):
        output='fixture'
        receipt=seal({'output_sha256':hashlib.sha256(output.encode()).hexdigest()})
        self.assertTrue(verify_receipt(receipt,output))
        for changes in [{'record_encoding':'unknown'},{'schema':'computepilot.receipt.v5'},{'schema':'FLOP_VERIFIED'}]:
            self.assertFalse(verify_receipt({**receipt,**changes},output))
        self.assertFalse(verify_receipt({'record_sha256':None},output))


if __name__=='__main__':unittest.main()
