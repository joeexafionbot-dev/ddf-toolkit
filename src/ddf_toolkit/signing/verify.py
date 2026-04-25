"""DDF signature verification."""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _load_public_key(key_path: Path) -> ec.EllipticCurvePublicKey:
    key_data = key_path.read_bytes()
    key = serialization.load_pem_public_key(key_data)
    if not isinstance(key, ec.EllipticCurvePublicKey):
        msg = "Key is not an ECDSA public key"
        raise TypeError(msg)
    return key


def verify_ddf(file: Path, key: Path | None = None) -> bool:
    """Verify a signed DDF file.

    Returns True if valid, False if invalid.
    """
    if key is None:
        key = Path.home() / ".config" / "ddf-toolkit" / "test-key.pub"

    if not key.exists():
        msg = f"Public key not found: {key}"
        raise FileNotFoundError(msg)

    public_key = _load_public_key(key)
    raw = file.read_bytes()

    # Find signature metadata line
    marker = b"# DDF-TOOLKIT-SIG "
    idx = raw.rfind(marker)
    if idx == -1:
        return False

    sig_line = raw[idx:].split(b"\n", 1)[0].decode()
    parts = {}
    for part in sig_line[len("# DDF-TOOLKIT-SIG ") :].split():
        k, _, v = part.partition("=")
        parts[k] = v

    if "body_len" not in parts or "sig" not in parts:
        return False

    body_len = int(parts["body_len"])
    signature = bytes.fromhex(parts["sig"])
    body = raw[:body_len]

    try:
        public_key.verify(signature, body, ec.ECDSA(hashes.SHA384()))
        return True
    except Exception:
        return False
