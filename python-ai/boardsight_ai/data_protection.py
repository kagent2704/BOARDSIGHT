from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENC_PREFIX = "bsenc:v1:"
ENCRYPTED_DATA_UNAVAILABLE = "[encrypted-data-unavailable]"


def data_encryption_secret() -> str:
    return (os.getenv("BOARDSIGHT_DATA_ENCRYPTION_KEY") or "").strip()


def data_encryption_enabled() -> bool:
    return bool(data_encryption_secret())


def data_encryption_key_fingerprint() -> str:
    secret = data_encryption_secret()
    if not secret:
        return ""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]


def _aesgcm() -> AESGCM:
    secret = data_encryption_secret()
    if not secret:
        raise RuntimeError("BOARDSIGHT_DATA_ENCRYPTION_KEY is required to decrypt protected data.")
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    return AESGCM(key)


def is_encrypted_text(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(ENC_PREFIX)


def encrypt_text(value: Any) -> Any:
    if value is None:
        return None
    text = str(value)
    if not data_encryption_enabled() or is_encrypted_text(text):
        return text
    aesgcm = _aesgcm()
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, text.encode("utf-8"), None)
    token = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{ENC_PREFIX}{token}"


def decrypt_text(value: Any, *, missing_key_placeholder: str | None = ENCRYPTED_DATA_UNAVAILABLE) -> Any:
    if value is None or not isinstance(value, str) or not is_encrypted_text(value):
        return value
    secret = data_encryption_secret()
    if not secret:
        if missing_key_placeholder is None:
            raise RuntimeError("Protected data exists but BOARDSIGHT_DATA_ENCRYPTION_KEY is not configured.")
        return missing_key_placeholder
    token = value[len(ENC_PREFIX):]
    payload = base64.urlsafe_b64decode(token.encode("ascii"))
    nonce, ciphertext = payload[:12], payload[12:]
    plaintext = _aesgcm().decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def decrypt_json_text(value: Any) -> str:
    decrypted = decrypt_text(value, missing_key_placeholder=None)
    return str(decrypted or "")


def write_protected_json(path: Path, payload: dict[str, Any]) -> Path:
    serialized = json.dumps(payload, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    if data_encryption_enabled():
        path.write_text(str(encrypt_text(serialized)), encoding="utf-8")
    else:
        path.write_text(serialized, encoding="utf-8")
    return path

