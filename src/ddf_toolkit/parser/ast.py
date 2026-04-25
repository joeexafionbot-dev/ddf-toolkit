"""Typed AST dataclasses for DDF files.

The structure follows the actual DDF file format as observed in the pilot DDFs,
not the original PRD prediction. See docs/internal/SPRINT_0_AMENDMENTS.md Section 2.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

import yaml


@dataclass(frozen=True)
class SignatureSection:
    sign_algo: str
    sign_date: str
    file_verdate: str
    signature: str


@dataclass(frozen=True)
class ConnectionConfig:
    connection: str
    authentification: str
    domain: str
    domain_alt: str | None = None
    slavesmax: int | None = None


@dataclass(frozen=True)
class GeneralMetadata:
    device: str
    manufacturer: str
    type: str
    protocol: str
    model_nr: str
    version_nr: str
    id: str
    min_control_version: str
    timestamp: str
    version_info: str | None = None
    version_user: str | None = None
    revision: str | None = None


@dataclass(frozen=True)
class GeneralParams:
    """Connection, auth, and runtime parameters from the second *GENERAL block."""

    connection: str
    authentification: str
    domain: str
    domain_alt: str | None = None
    slavesmax: int | None = None
    debugport: int | None = None
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandDef:
    id: int
    alias: str
    formula: str


@dataclass(frozen=True)
class ConfigField:
    id: int
    alias: str


@dataclass(frozen=True)
class ArgsDef:
    method: str | None
    alias: str
    type: str | None
    name: str
    value: str
    item: str | None = None
    format: str | None = None


@dataclass(frozen=True)
class WriteCommand:
    alias: str
    method: str
    url: str | None
    datatype: str | None
    formula: str
    args: list[ArgsDef] = field(default_factory=list)


@dataclass(frozen=True)
class ReadCommand:
    alias: str
    method: str
    url: str
    datatype: str
    polling: int | None = None


@dataclass(frozen=True)
class Item:
    alias: str
    name: str
    id: int
    visibility: str | None = None
    unit: str | None = None
    type: str | None = None
    default: str | None = None
    wformula: str | None = None
    rformula: str | None = None
    polling: int | None = None
    comment: str | None = None


@dataclass(frozen=True)
class Group:
    id: int
    alias: str
    name: str


@dataclass(frozen=True)
class ObjectDef:
    group: int
    id: int
    alias: str
    type: int | None = None
    enum: int | None = None
    enumtext: str | None = None
    enumval: str | None = None
    min: float | None = None
    max: float | None = None
    iotype: int | None = None
    digits: int | None = None
    itemid: int | None = None
    unit: str | None = None
    alarm: str | None = None
    alarmval: str | None = None
    alarmtime: int | None = None
    outtype: int | None = None
    cmditemid: int | None = None
    command: str | None = None
    commandenum: str | None = None
    commandval: str | None = None
    viewtype: int | None = None
    log: int | None = None


@dataclass
class DDF:
    signature: SignatureSection | None
    general_metadata: GeneralMetadata
    general_params: GeneralParams
    commands: list[CommandDef]
    config: list[ConfigField]
    reads: list[ReadCommand]
    writes: list[WriteCommand]
    items: list[Item]
    groups: list[Group]
    objects: list[ObjectDef]
    raw_source: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        del d["raw_source"]
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)
