import jwt
import pytest

from app.core.security import decode_token, hash_password, make_token, verify_password


def test_password_hash_roundtrip():
    h = hash_password("Demo@1234")
    assert h != "Demo@1234"
    assert verify_password("Demo@1234", h)
    assert not verify_password("wrong", h)


def test_access_token_decodes_as_access_only():
    t = make_token("u1", "access")
    assert decode_token(t, "access")["sub"] == "u1"
    with pytest.raises(jwt.PyJWTError):
        decode_token(t, "refresh")


def test_refresh_token_is_not_an_access_token():
    t = make_token("u1", "refresh")
    with pytest.raises(jwt.PyJWTError):
        decode_token(t, "access")


def test_expired_token_is_rejected():
    t = make_token("u1", "access", minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(t, "access")


def test_tampered_token_is_rejected():
    t = make_token("u1", "access")
    bad = t[:-2] + ("AA" if not t.endswith("AA") else "BB")
    with pytest.raises(jwt.PyJWTError):
        decode_token(bad, "access")
