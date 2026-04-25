"""DDF signing with ECDSA-SHA384."""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _load_private_key(key_path: Path) -> ec.EllipticCurvePrivateKey:
    key_data = key_path.read_bytes()
    key = serialization.load_pem_private_key(key_data, password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        msg = "Key is not an ECDSA private key"
        raise TypeError(msg)
    return key


def sign_ddf(
    file: Path,
    key: Path | None = None,
    test: bool = False,
    output: Path | None = None,
) -> None:
    """Sign a DDF file with ECDSA-SHA384.

    If test=True, uses the default test key from ~/.config/ddf-toolkit/.
    """
    if test and not key:
        key = Path.home() / ".config" / "ddf-toolkit" / "test-key.pem"
        if not key.exists():
            msg = "Test key not found. Run `ddf keygen --test` first."
            raise FileNotFoundError(msg)

    if key is None:
        msg = "No key provided"
        raise ValueError(msg)

    private_key = _load_private_key(key)
    ddf_bytes = file.read_bytes()
    signature = private_key.sign(ddf_bytes, ec.ECDSA(hashes.SHA384()))

    # Store body length so verify can reconstruct exact original bytes
    out_path = output or file
    out_path.write_bytes(
        ddf_bytes
        + f"\n# DDF-TOOLKIT-SIG body_len={len(ddf_bytes)} sig={signature.hex()}\n".encode()
    )
