from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    password = "StrongPass123!"
    encoded = hash_password(password)
    assert verify_password(password, encoded)
    assert not verify_password("wrong-password", encoded)


def test_token_roundtrip() -> None:
    token = create_access_token("42", {"role": "owner"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "owner"
    assert payload["type"] == "access"
