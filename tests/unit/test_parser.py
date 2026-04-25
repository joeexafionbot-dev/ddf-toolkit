"""Tests for the DDF parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from ddf_toolkit.parser import parse_ddf

FIXTURES = Path(__file__).parent.parent / "fixtures" / "ddfs"


class TestParserMicrosoftCalendar:
    """Parse the Microsoft Calendar pilot DDF."""

    @pytest.fixture()
    def ddf(self):
        path = FIXTURES / "Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"
        return parse_ddf(path)

    def test_general_metadata(self, ddf):
        assert ddf.general_metadata.device == "Calender"
        assert ddf.general_metadata.manufacturer == "Microsoft"
        assert ddf.general_metadata.type == "Gateway"
        assert ddf.general_metadata.protocol == "REST-API (DDF)"
        assert ddf.general_metadata.id == "0x0D00007700010100"

    def test_general_params(self, ddf):
        assert ddf.general_params.debugport == 8500
        assert ddf.general_params.domain == "https://graph.microsoft.com"

    def test_signature(self, ddf):
        assert ddf.signature is not None
        assert ddf.signature.sign_algo == "ECDSA-SHA384"
        assert len(ddf.signature.signature) > 0

    def test_commands(self, ddf):
        assert len(ddf.commands) >= 2
        aliases = [c.alias for c in ddf.commands]
        assert "GETTOKEN" in aliases
        assert "GETSLAVESROOMS" in aliases

    def test_config(self, ddf):
        assert len(ddf.config) == 3
        aliases = [c.alias for c in ddf.config]
        assert "TENANTID" in aliases
        assert "CLIENTID" in aliases
        assert "SECRET" in aliases

    def test_writes(self, ddf):
        assert len(ddf.writes) >= 3
        aliases = [w.alias for w in ddf.writes]
        assert "GETTOKEN" in aliases

    def test_write_args(self, ddf):
        gettoken = next(w for w in ddf.writes if w.alias == "GETTOKEN")
        assert len(gettoken.args) >= 5

    def test_items(self, ddf):
        assert len(ddf.items) >= 15
        aliases = [i.alias for i in ddf.items]
        assert "COUNT" in aliases
        assert "SUBJECT" in aliases

    def test_groups(self, ddf):
        assert len(ddf.groups) >= 2

    def test_objects(self, ddf):
        assert len(ddf.objects) >= 10

    def test_raw_source_preserved(self, ddf):
        assert len(ddf.raw_source) > 0
        assert "*GENERAL" in ddf.raw_source


class TestParserDaikinStylish:
    """Parse the Daikin Stylish pilot DDF."""

    @pytest.fixture()
    def ddf(self):
        path = FIXTURES / "Daikin.Air conditioner.REST-API (DDF).Stylish.1(0x0D00000D00010100).csv"
        return parse_ddf(path)

    def test_general_metadata(self, ddf):
        assert ddf.general_metadata.device == "Stylish"
        assert ddf.general_metadata.manufacturer == "Daikin"
        assert ddf.general_metadata.type == "Air conditioner"

    def test_general_params(self, ddf):
        assert ddf.general_params.authentification == "OAUTH_DEVICE_FLOW"
        assert ddf.general_params.debugport == 8500

    def test_signature(self, ddf):
        assert ddf.signature is not None
        assert ddf.signature.sign_algo == "ECDSA-SHA384"

    def test_writes(self, ddf):
        assert len(ddf.writes) >= 5
        aliases = [w.alias for w in ddf.writes]
        assert "GETDATA" in aliases
        assert "REFRESHTOKEN" in aliases

    def test_items(self, ddf):
        assert len(ddf.items) >= 20

    def test_objects(self, ddf):
        assert len(ddf.objects) >= 10


class TestParserToJson:
    def test_to_json_roundtrip(self):
        path = FIXTURES / "Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"
        ddf = parse_ddf(path)
        json_str = ddf.to_json()
        assert '"device": "Calender"' in json_str


class TestParserToYaml:
    def test_to_yaml_roundtrip(self):
        path = FIXTURES / "Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"
        ddf = parse_ddf(path)
        yaml_str = ddf.to_yaml()
        assert "device: Calender" in yaml_str
