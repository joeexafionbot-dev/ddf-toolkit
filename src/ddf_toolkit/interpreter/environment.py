"""Pluggable runtime environment for the DDF interpreter.

The Environment encapsulates all external state and side effects:
- $.GPARAM, $.SYS, $.CONFIG, $.PARAM namespaces
- X.n item variables
- WRITE trigger flags and HTTP response state
- Side-effect handlers (DEBUG, SAVE_JSON, RANDOMSTRING, SYSTEMINFO)

Test mode: side effects captured into accumulators for assertions.
Production mode: side effects execute against real system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HttpResponse:
    """Response from an HTTP request."""

    status_code: int
    body: Any = None
    raw_data: str = ""
    url: str = ""
    timestamp: float = 0.0


@dataclass
class WriteState:
    """Runtime state for a *WRITE command."""

    alias: str
    trigger: bool = False  # .F flag
    http_response: HttpResponse | None = None
    timestamp: float = 0.0  # .T


@dataclass
class Environment:
    """Runtime context for DDF script execution.

    All external access goes through this abstraction.
    Default implementation is test-friendly (deterministic, captured side effects).
    """

    # -- State namespaces --
    gparams: dict[str, Any] = field(default_factory=dict)
    sys_vars: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    items: dict[int, Any] = field(default_factory=dict)  # X.n variables
    temp_vars: dict[str, Any] = field(default_factory=dict)  # named temp vars

    # -- Write command states --
    write_states: dict[str, WriteState] = field(default_factory=dict)

    # -- Side-effect accumulators (test mode) --
    debug_log: list[str] = field(default_factory=list)
    saved_json: dict[str, Any] = field(default_factory=dict)
    http_requests: list[dict[str, Any]] = field(default_factory=list)

    # -- Time control --
    _frozen_time: float | None = None

    def now(self) -> float:
        """Current time as epoch seconds. Frozen in test mode."""
        if self._frozen_time is not None:
            return self._frozen_time
        return time.time()

    def freeze_time(self, epoch: float) -> None:
        """Set a fixed time for deterministic testing."""
        self._frozen_time = epoch
        self.sys_vars["TIME"] = epoch

    # -- Variable access (called by interpreter) --

    def get_var(self, path: list[str]) -> Any:
        """Resolve a dot-separated variable path.

        Supports: $.GPARAM.x, $.SYS.TIME, $.CONFIG.n, $.PARAM.x, X.n, ALIAS.F, etc.
        """
        if not path:
            return None

        root = path[0]

        # $ paths: $.GPARAM.x, $.SYS.TIME, $.CONFIG.n, $.PARAM.x
        if root == "$" and len(path) >= 2:
            namespace = path[1]
            rest = path[2:]

            if namespace == "GPARAM":
                return self._resolve_dict(self.gparams, rest)
            if namespace == "SYS":
                if rest == ["TIME"]:
                    return self.now()
                if rest == ["TIME_MS"]:
                    return self.now() * 1000
                return self._resolve_dict(self.sys_vars, rest)
            if namespace == "CONFIG":
                return self._resolve_dict(self.config, rest)
            if namespace == "PARAM":
                return self._resolve_dict(self.params, rest)
            return None

        # X.n item variables
        if root == "X" and len(path) == 2:
            try:
                item_id = int(path[1])
                return self.items.get(item_id, 0)
            except ValueError:
                pass

        # ALIAS.F (trigger flag), ALIAS.HTTP_CODE, ALIAS.VALUE.*, etc.
        if root in self.write_states and len(path) >= 2:
            ws = self.write_states[root]
            prop = path[1]
            if prop == "F":
                return 1 if ws.trigger else 0
            if prop == "T":
                return ws.timestamp
            if ws.http_response:
                if prop == "HTTP_CODE":
                    return ws.http_response.status_code
                if prop == "HTTP_DATA":
                    return ws.http_response.raw_data
                if prop == "URL":
                    return ws.http_response.url
                if prop == "VALUE":
                    return self._resolve_json(ws.http_response.body, path[2:])
                if prop == "ARRAY":
                    return self._resolve_array_op(ws.http_response.body, path[2:])
                if prop == "ASLIST":
                    return self._resolve_aslist(ws.http_response.body, path[2:])
            return None

        # Named temp variable (single identifier)
        if len(path) == 1:
            return self.temp_vars.get(root, 0)

        # Multi-part path in temp namespace
        return self.temp_vars.get(".".join(path), 0)

    def set_var(self, path: list[str], value: Any) -> None:
        """Set a variable at the given path."""
        if not path:
            return

        root = path[0]

        # $.GPARAM.x
        if root == "$" and len(path) >= 3:
            namespace = path[1]
            if namespace == "GPARAM":
                self._set_nested(self.gparams, path[2:], value)
                return
            if namespace == "CONFIG":
                self._set_nested(self.config, path[2:], value)
                return
            if namespace == "PARAM":
                self._set_nested(self.params, path[2:], value)
                return
            return

        # X.n
        if root == "X" and len(path) == 2:
            try:
                item_id = int(path[1])
                self.items[item_id] = value
                return
            except ValueError:
                pass

        # ALIAS.F (trigger flag)
        if root in self.write_states and len(path) == 2:
            ws = self.write_states[root]
            if path[1] == "F":
                ws.trigger = bool(value)
                return
            if path[1] == "T":
                ws.timestamp = float(value)
                return

        # Named temp variable
        if len(path) == 1:
            self.temp_vars[root] = value
        else:
            self.temp_vars[".".join(path)] = value

    # -- Side-effect handlers --

    def debug(self, *args: Any) -> None:
        """Capture DEBUG output."""
        msg = ", ".join(str(a) for a in args)
        self.debug_log.append(msg)

    def save_json(self, *args: Any) -> None:
        """Capture SAVE_JSON call."""
        key = f"save_{len(self.saved_json)}"
        self.saved_json[key] = list(args)

    def random_string(self, length: int) -> str:
        """Return deterministic 'random' string in test mode."""
        return "A" * length

    def system_info(self, key: str) -> str:
        """Return system info."""
        if key.upper() == "NAME":
            return "ddf-toolkit-test"
        if key.upper() == "ID":
            return "TEST-0000-0000"
        return ""

    # -- Internal helpers --

    def _resolve_dict(self, d: dict[str, Any], keys: list[str]) -> Any:
        """Walk into a nested dict by key path."""
        current: Any = d
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key, current.get(key.upper(), None))
            else:
                return None
        return current

    def _resolve_json(self, data: Any, keys: list[str]) -> Any:
        """Resolve a JSON path into response body."""
        current = data
        for key in keys:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                try:
                    idx = int(key)
                    current = current[idx] if idx < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current

    def _resolve_array_op(self, data: Any, keys: list[str]) -> Any:
        """Resolve ARRAY operations: ARRAY.LEN.path, ARRAY.MAX.path, etc."""
        if not keys:
            return None
        op = keys[0]
        rest = keys[1:]
        arr = self._resolve_json(data, rest)
        if not isinstance(arr, list):
            return 0
        if op == "LEN":
            return len(arr)
        if op == "MAX":
            return max(arr) if arr else 0
        if op == "MIN":
            return min(arr) if arr else 0
        if op == "MEDIA":
            return sum(arr) / len(arr) if arr else 0
        return None

    def _resolve_aslist(self, data: Any, keys: list[str]) -> str:
        """Resolve ASLIST: extract values from array into comma-separated string."""
        # Simplified: walk the path, collect values
        result = self._resolve_json(data, keys)
        if isinstance(result, list):
            return ",".join(str(v) for v in result)
        return str(result) if result is not None else ""

    def _set_nested(self, d: dict[str, Any], keys: list[str], value: Any) -> None:
        """Set a value in a nested dict, creating intermediate dicts as needed."""
        for key in keys[:-1]:
            if key not in d or not isinstance(d[key], dict):
                d[key] = {}
            d = d[key]
        if keys:
            d[keys[-1]] = value
