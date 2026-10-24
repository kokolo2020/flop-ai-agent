"""computepilot.json.v1, shared with public/receipt-core.js; unsigned local hashes."""
import hashlib
import json

SCHEMA = 'computepilot.receipt.v6'
ENCODING = 'computepilot.json.v1'


def canonical(value):
    seen = set()

    def encode(v, depth):
        if depth > 100:
            raise ValueError('Receipt nesting limit exceeded')
        if v is None:
            return 'null'
        if type(v) is bool:
            return 'true' if v else 'false'
        if type(v) is str:
            if any(0xd800 <= ord(c) <= 0xdfff for c in v):
                raise ValueError('Unpaired Unicode surrogate')
            return json.dumps(v, ensure_ascii=False)
        if type(v) is int:
            if not -(2**53-1) <= v <= 2**53-1:
                raise ValueError('Use safe integers or decimal strings in receipts')
            return str(v)
        if type(v) not in (dict,list) or id(v) in seen:
            raise ValueError('Expected acyclic JSON values')
        seen.add(id(v))
        if type(v) is list:
            result = '[' + ','.join(encode(x,depth+1) for x in v) + ']'
        else:
            if not all(type(k) is str for k in v):
                raise ValueError('Expected string object keys')
            result = '{' + ','.join(encode(k,depth+1)+':'+encode(v[k],depth+1) for k in sorted(v)) + '}'
        seen.remove(id(v))
        return result
    return encode(value,0)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def seal(body):
    if type(body) is not dict or 'record_sha256' in body:
        raise ValueError('Expected unsealed receipt body')
    record = {**body,'schema':SCHEMA,'record_encoding':ENCODING}
    return {**record,'record_sha256':digest(record)}


def verify_receipt(receipt, output):
    try:
        if type(receipt) is not dict or type(output) is not str or len(receipt.get('record_sha256','')) != 64:
            return False
        body = {k:v for k,v in receipt.items() if k != 'record_sha256'}
        if hashlib.sha256(output.encode('utf-8')).hexdigest() != receipt.get('output_sha256'):
            return False
        if receipt.get('schema') == SCHEMA and receipt.get('record_encoding') == ENCODING:
            return digest(body) == receipt['record_sha256']
        if receipt.get('schema') == 'computepilot.receipt.v5' and 'record_encoding' not in receipt:
            sorted_hash = digest(body)  # Validates the same restricted JSON domain.
            legacy = hashlib.sha256(json.dumps(body,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()
            return receipt['record_sha256'] in (sorted_hash,legacy)
        return False
    except (ValueError,TypeError,UnicodeError,RecursionError):
        return False
