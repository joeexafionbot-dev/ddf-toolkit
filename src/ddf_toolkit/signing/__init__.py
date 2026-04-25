"""DDF signing — ECDSA-SHA384 test-key signing and verification."""

from __future__ import annotations

from ddf_toolkit.signing.keys import generate_test_keypair
from ddf_toolkit.signing.sign import sign_ddf
from ddf_toolkit.signing.verify import verify_ddf

__all__ = ["generate_test_keypair", "sign_ddf", "verify_ddf"]
