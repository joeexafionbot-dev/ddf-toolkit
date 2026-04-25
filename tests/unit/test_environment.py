"""Tests for the interpreter Environment."""

from __future__ import annotations

from ddf_toolkit.interpreter.environment import Environment, HttpResponse, WriteState


def test_get_sys_time():
    env = Environment()
    env.freeze_time(12345.0)
    assert env.get_var(["$", "SYS", "TIME"]) == 12345.0


def test_get_sys_time_ms():
    env = Environment()
    env.freeze_time(1.5)
    assert env.get_var(["$", "SYS", "TIME_MS"]) == 1500.0


def test_get_config():
    env = Environment()
    env.config["0"] = "tenant-id"
    assert env.get_var(["$", "CONFIG", "0"]) == "tenant-id"


def test_get_param():
    env = Environment()
    env.params["SLAVE"] = "device1"
    assert env.get_var(["$", "PARAM", "SLAVE"]) == "device1"


def test_set_gparam_nested():
    env = Environment()
    env.set_var(["$", "GPARAM", "AUTH", "TOKEN"], "abc")
    assert env.gparams["AUTH"]["TOKEN"] == "abc"


def test_set_config():
    env = Environment()
    env.set_var(["$", "CONFIG", "0"], "value")
    assert env.config["0"] == "value"


def test_set_param():
    env = Environment()
    env.set_var(["$", "PARAM", "SLAVE"], "dev1")
    assert env.params["SLAVE"] == "dev1"


def test_write_state_timestamp():
    env = Environment()
    env.write_states["W"] = WriteState(alias="W")
    env.set_var(["W", "T"], 999.0)
    assert env.get_var(["W", "T"]) == 999.0


def test_write_state_http_data():
    env = Environment()
    env.write_states["W"] = WriteState(
        alias="W",
        http_response=HttpResponse(status_code=404, raw_data='{"error": "not found"}', url="/test"),
    )
    assert env.get_var(["W", "HTTP_DATA"]) == '{"error": "not found"}'
    assert env.get_var(["W", "URL"]) == "/test"


def test_write_state_no_response():
    env = Environment()
    env.write_states["W"] = WriteState(alias="W")
    assert env.get_var(["W", "HTTP_CODE"]) is None
    assert env.get_var(["W", "VALUE", "x"]) is None


def test_array_operations():
    env = Environment()
    env.write_states["R"] = WriteState(
        alias="R",
        http_response=HttpResponse(
            status_code=200,
            body={"items": [10, 20, 30, 40]},
        ),
    )
    assert env.get_var(["R", "ARRAY", "LEN", "items"]) == 4
    assert env.get_var(["R", "ARRAY", "MAX", "items"]) == 40
    assert env.get_var(["R", "ARRAY", "MIN", "items"]) == 10
    assert env.get_var(["R", "ARRAY", "MEDIA", "items"]) == 25.0


def test_array_empty():
    env = Environment()
    env.write_states["R"] = WriteState(
        alias="R",
        http_response=HttpResponse(status_code=200, body={"items": []}),
    )
    assert env.get_var(["R", "ARRAY", "LEN", "items"]) == 0
    assert env.get_var(["R", "ARRAY", "MAX", "items"]) == 0


def test_array_non_list():
    env = Environment()
    env.write_states["R"] = WriteState(
        alias="R",
        http_response=HttpResponse(status_code=200, body={"val": 42}),
    )
    assert env.get_var(["R", "ARRAY", "LEN", "val"]) == 0


def test_aslist():
    env = Environment()
    env.write_states["R"] = WriteState(
        alias="R",
        http_response=HttpResponse(
            status_code=200,
            body={"values": ["a", "b", "c"]},
        ),
    )
    assert env.get_var(["R", "ASLIST", "values"]) == "a,b,c"


def test_json_nested_access():
    env = Environment()
    env.write_states["R"] = WriteState(
        alias="R",
        http_response=HttpResponse(
            status_code=200,
            body={"a": {"b": {"c": 42}}},
        ),
    )
    assert env.get_var(["R", "VALUE", "a", "b", "c"]) == 42


def test_json_list_index():
    env = Environment()
    env.write_states["R"] = WriteState(
        alias="R",
        http_response=HttpResponse(
            status_code=200,
            body={"items": [{"name": "first"}, {"name": "second"}]},
        ),
    )
    assert env.get_var(["R", "VALUE", "items", "0", "name"]) == "first"
    assert env.get_var(["R", "VALUE", "items", "1", "name"]) == "second"


def test_resolve_unknown_path():
    env = Environment()
    assert env.get_var(["$", "UNKNOWN", "x"]) is None
    assert env.get_var([]) is None


def test_temp_var_multipart():
    env = Environment()
    env.set_var(["MY", "VAR"], 42)
    assert env.get_var(["MY", "VAR"]) == 42


def test_now_unfrozen():
    env = Environment()
    t = env.now()
    assert t > 0


def test_system_info_name():
    env = Environment()
    assert env.system_info("NAME") == "ddf-toolkit-test"
    assert env.system_info("unknown") == ""
