"""ECDSA P-384 test keypair generation."""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _default_key_dir() -> Path:
    d = Path.home() / ".config" / "ddf-toolkit"
    d.mkdir(parents=True, exist_ok=True)
    return d


def generate_test_keypair(
    output: Path | None = None,
) -> tuple[Path, Path]:
    """Generate an ECDSA P-384 test keypair.

    Returns (private_key_path, public_key_path).
    """
    private_key = ec.generate_private_key(ec.SECP384R1())

    if output:
        private_path = output
        public_path = output.with_suffix(".pub")
    else:
        key_dir = _default_key_dir()
        private_path = key_dir / "test-key.pem"
        public_path = key_dir / "test-key.pub"

    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    return private_path, public_path
