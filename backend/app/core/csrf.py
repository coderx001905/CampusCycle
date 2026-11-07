import base64
import hashlib
import hmac
import secrets
import time


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def issue_csrf_token(*, secret: str, refresh_token: str, lifetime_seconds: int = 7 * 24 * 3600) -> str:
    expiry = int(time.time()) + lifetime_seconds
    nonce = _b64(secrets.token_bytes(32))
    binding = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    payload = f"{expiry}.{nonce}.{binding}"
    signature = _b64(hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def verify_csrf_token(*, token: str, secret: str, refresh_token: str) -> bool:
    try:
        expiry_text, nonce, binding, signature = token.split(".", 3)
        expiry = int(expiry_text)
        if expiry < int(time.time()) or len(nonce) < 32:
            return False
        expected_binding = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(binding, expected_binding):
            return False
        payload = f"{expiry_text}.{nonce}.{binding}"
        expected = _b64(hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest())
        return hmac.compare_digest(signature, expected)
    except (ValueError, TypeError, UnicodeError):
        return False
