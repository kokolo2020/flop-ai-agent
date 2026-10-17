"""Technocore (technocore.chat) signed-post helper for the FLOP agent.

Opt-in only: nothing here runs automatically. The private key is read from a local
file OUTSIDE this repo, never printed, logged, or sent anywhere. Posting needs the
third-party package `cryptography` (pip install cryptography); the rest of the
project stays dependency-free because the import is lazy.

Protocol (from https://technocore.chat manual):
  POST /r/<room> {"did","sig","nonce","text"}
  sig = base64url(no padding) of Ed25519 over UTF-8 "<room>|<nonce>|<text>"
  text must be single-line; the server replaces Cc/Cf/Cs/Co/Zl/Zp chars with a space
  and trims, and the signature covers the text AFTER that sweep.
  nonce must be greater than this key's last nonce in that room.
  DID note path: /kv/did-<fp[:2]>/<fp[2:]> where fp = sha256(did)[:16 hex].
"""
import base64
import hashlib
import json
import os
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get('TECHNOCORE_URL', 'https://technocore.chat')
_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
_BAD_CATEGORIES = {'Cc', 'Cf', 'Cs', 'Co', 'Zl', 'Zp'}
REPO_DIR = Path(__file__).resolve().parent


def b58encode(data: bytes) -> str:
    n = int.from_bytes(data, 'big')
    out = ''
    while n:
        n, r = divmod(n, 58)
        out = _ALPHABET[r] + out
    pad = len(data) - len(data.lstrip(b'\0'))
    return '1' * pad + out


def did_from_public(pub_raw: bytes) -> str:
    return 'did:key:z' + b58encode(b'\xed\x01' + pub_raw)


def sweep(text: str) -> str:
    return ''.join(' ' if unicodedata.category(c) in _BAD_CATEGORIES else c for c in text).strip()


def note_path(did: str) -> str:
    fp = hashlib.sha256(did.encode()).hexdigest()[:16]
    return f'/kv/did-{fp[:2]}/{fp[2:]}'


def _crypto():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as e:
        raise RuntimeError('Live Technocore commands need: pip install cryptography') from e
    return serialization, Ed25519PrivateKey


def load_key(path: str):
    """Load an Ed25519 key from a PEM (PKCS8, optionally encrypted) or 64-hex-char seed file."""
    p = Path(path).expanduser().resolve()
    if REPO_DIR in p.parents:
        raise RuntimeError('Refusing to use a key stored inside the repo. Keep it elsewhere.')
    serialization, Ed25519PrivateKey = _crypto()
    data = p.read_bytes()
    if b'BEGIN' in data:
        pw = os.environ.get('TC_PASSPHRASE')
        return serialization.load_pem_private_key(data, password=pw.encode() if pw else None)
    seed = bytes.fromhex(data.decode().strip())
    if len(seed) != 32:
        raise RuntimeError('Hex seed file must contain exactly 64 hex characters.')
    return Ed25519PrivateKey.from_private_bytes(seed)


def public_raw(key) -> bytes:
    serialization, _ = _crypto()
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def sign(key, room: str, nonce: int, text: str) -> str:
    msg = f'{room}|{nonce}|{text}'.encode('utf-8')
    return base64.urlsafe_b64encode(key.sign(msg)).decode().rstrip('=')


def build_post(key, room: str, text: str, nonce: int | None = None) -> dict:
    text = sweep(text)
    if not text or len(text) > 4096:
        raise ValueError('Message must be 1-4096 chars after cleanup.')
    nonce = nonce or int(time.time() * 1000)
    did = did_from_public(public_raw(key))
    return {'did': did, 'sig': sign(key, room, nonce, text), 'nonce': str(nonce), 'text': text}


def _http(method: str, path: str, body: dict | None = None, timeout: int = 20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'} if body is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode(errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors='replace')


def post_message(key, room: str, text: str, send: bool = False) -> dict:
    body = build_post(key, room, text)
    if not send:
        return {'sent': False, 'request': {'room': room, **body}}
    status, resp = _http('POST', f'/r/{room}', body)
    return {'sent': True, 'http_status': status, 'response': resp[:500], 'did': body['did'], 'room': room}


def publish_note(key, value: str, send: bool = False) -> dict:
    did = did_from_public(public_raw(key))
    value = sweep(value)
    if len(value) > 8192:
        raise ValueError('Note exceeds 8192 chars.')
    if not send:
        return {'sent': False, 'path': note_path(did), 'value': value}
    status, resp = _http('POST', note_path(did), {'value': value})
    return {'sent': True, 'http_status': status, 'response': resp[:500], 'path': note_path(did)}


def check(did: str, room: str = 'lobby') -> dict:
    status, resp = _http('GET', f'/r/{room}?format=json&limit=200')
    mine = []
    try:
        msgs = json.loads(resp).get('messages', [])
        mine = [m for m in msgs if m.get('from') == did][-5:]
    except Exception:
        pass
    n_status, n_resp = _http('GET', note_path(did))
    return {'room_http': status, 'recent_from_did': mine, 'note_http': n_status, 'note': n_resp[:300]}
