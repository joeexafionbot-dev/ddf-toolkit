"""Tests for DDF signing and verification."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ddf_toolkit.signing.keys import generate_test_keypair
from ddf_toolkit.signing.sign import sign_ddf
from ddf_toolkit.signing.verify import verify_ddf

FIXTURES = Path(__file__).parent.parent / "fixtures" / "ddfs"


@pytest.fixture()
def key_dir(tmp_path):
    """Generate a test keypair in a temp directory."""
    private_path = tmp_path / "test-key.pem"
    priv, pub = generate_test_keypair(output=private_path)
    return priv, pub


@pytest.fixture()
def ddf_copy(tmp_path):
    """Copy the MS Calendar DDF to a temp directory."""
    src = FIXTURES / "Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"
    dst = tmp_path / "calendar.csv"
    shutil.copy(src, dst)
    return dst


def test_keygen(key_dir):
    priv, pub = key_dir
    assert priv.exists()
    assert pub.exists()
    assert priv.read_bytes().startswith(b"-----BEGIN PRIVATE KEY-----")
    assert pub.read_bytes().startswith(b"-----BEGIN PUBLIC KEY-----")


def test_sign_and_verify(key_dir, ddf_copy, tmp_path):
    priv, pub = key_dir
    signed_path = tmp_path / "signed.csv"
    sign_ddf(ddf_copy, key=priv, output=signed_path)
    assert signed_path.exists()
    assert verify_ddf(signed_path, key=pub)


def test_tampered_file_fails_verification(key_dir, ddf_copy, tmp_path):
    priv, pub = key_dir
    signed_path = tmp_path / "signed.csv"
    sign_ddf(ddf_copy, key=priv, output=signed_path)

    # Tamper with the signed file
    content = signed_path.read_bytes()
    tampered = content.replace(b"Calender", b"TAMPERED")
    signed_path.write_bytes(tampered)

    assert not verify_ddf(signed_path, key=pub)


def test_verify_unsigned_file_returns_false(key_dir, ddf_copy):
    _, pub = key_dir
    assert not verify_ddf(ddf_copy, key=pub)


def test_sign_without_key_raises():
    with pytest.raises(ValueError, match="No key"):
        sign_ddf(Path("dummy.csv"), key=None, test=False)


def test_sign_with_missing_test_key_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Test key not found"):
        sign_ddf(Path("dummy.csv"), key=None, test=True)


def test_roundtrip_daikin(key_dir, tmp_path):
    """Sign and verify the Daikin DDF."""
    priv, pub = key_dir
    src = FIXTURES / "Daikin.Air conditioner.REST-API (DDF).Stylish.1(0x0D00000D00010100).csv"
    ddf_copy = tmp_path / "daikin.csv"
    shutil.copy(src, ddf_copy)
    signed_path = tmp_path / "daikin_signed.csv"
    sign_ddf(ddf_copy, key=priv, output=signed_path)
    assert verify_ddf(signed_path, key=pub)
