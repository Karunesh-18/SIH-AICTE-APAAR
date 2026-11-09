"""Ed25519 signing for verification tokens (JWT, alg EdDSA).

The private key lives in a gitignored file (default backend/keys/), generated on first run, or at
VERIFY_KEY_PATH. Only the public key is ever served. Verification pins the algorithm to EdDSA, so
`alg: none` and HS256-with-the-public-key-as-secret are refused before any signature check.
"""
import base64
import hashlib
import os
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.config import settings

ALG = "EdDSA"
REQUIRED = ["jti", "sub", "purpose", "fields", "iat", "exp", "iss"]
_key: Ed25519PrivateKey | None = None


def reset() -> None:
    global _key
    _key = None


def _path() -> Path:
    p = Path(settings.verify_key_path)
    return p if p.is_absolute() else Path(__file__).resolve().parents[2] / p


def private_key() -> Ed25519PrivateKey:
    global _key
    if _key is None:
        path = _path()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            pem = Ed25519PrivateKey.generate().private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption())
            try:  # "x": never overwrite a key another worker just created
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(pem)
            except FileExistsError:
                pass
        _key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    return _key


def public_raw_bytes() -> bytes:
    return private_key().public_key().public_bytes(serialization.Encoding.Raw,
                                                    serialization.PublicFormat.Raw)


def public_pem() -> str:
    return private_key().public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def key_id() -> str:
    return hashlib.sha256(public_raw_bytes()).hexdigest()[:16]


def public_jwk() -> dict:
    x = base64.urlsafe_b64encode(public_raw_bytes()).rstrip(b"=").decode()
    return {"kty": "OKP", "crv": "Ed25519", "x": x, "alg": ALG, "use": "sig", "kid": key_id()}


def sign(claims: dict) -> str:
    return jwt.encode(claims, private_key(), algorithm=ALG, headers={"kid": key_id()})


def verify(token: str, required: list[str] = REQUIRED) -> dict:
    """Signature, algorithm, issuer and claim presence. Expiry is the caller's job, so it can use
    the demo clock. Raises jwt.PyJWTError for anything wrong."""
    return jwt.decode(token, private_key().public_key(), algorithms=[ALG],
                      issuer=settings.verify_issuer,
                      options={"verify_exp": False, "verify_iat": False, "require": required})


def decode_unverified(token: str) -> dict:
    """Tests and diagnostics only: never use the result to make a decision."""
    return jwt.decode(token, options={"verify_signature": False})
