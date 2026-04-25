# Formula Operator Coverage

Operators found in the pilot DDFs (Microsoft Calendar + Daikin Stylish).
Sprint 0 parses all of these; execution is Sprint 1.

| Category | Operator | Sprint 0 (Parse) | Sprint 1 (Execute) |
|----------|----------|:-:|:-:|
| **Control Flow** | IF / THEN / ELSE / ENDIF | PASS | planned |
| | ELSE IF | PASS | planned |
| **Assignment** | `:=` | PASS | planned |
| **Comparison** | `==`, `!=`, `<`, `>`, `<=`, `>=` | PASS | planned |
| **Logical** | `&&` (AND) | PASS | planned |
| | `\|\|` (OR) | PASS | planned |
| **Arithmetic** | `+`, `-`, `*`, `/` | PASS | planned |
| **Path Access** | `$.GPARAM.*` | PASS | planned |
| | `$.SYS.TIME` | PASS | planned |
| | `$.CONFIG.*` | PASS | planned |
| | `$.PARAM.*` | PASS | planned |
| | `ALIAS.VALUE.path[i].field` | PASS | planned |
| | `ALIAS.HTTP_CODE` | PASS | planned |
| | `ALIAS.HTTP_DATA` | PASS | planned |
| | `ALIAS.ARRAY.LEN.path` | PASS | planned |
| | `ALIAS.ASLIST.path[].field` | PASS | planned |
| | `ALIAS.T` (timestamp) | PASS | planned |
| | `ALIAS.F` (trigger flag) | PASS | planned |
| **Functions** | `ISEQUAL(a, b)` | PASS | planned |
| | `LEN(str)` | PASS | planned |
| | `CONCAT(a, b, ...)` | PASS | planned |
| | `SUBSTRING(str, start, len)` | PASS | planned |
| | `DECIMAL_TO_STRING(num)` | PASS | planned |
| | `REPLACEWITHASCII(str, s, c)` | PASS | planned |
| | `DATE(timestamp)` | PASS | planned |
| | `DEC(value, divisor)` | PASS | planned |
| | `DEBUG(value)` | PASS | planned |
| | `SYSTEMINFO(field)` | PASS | planned |
| | `RANDOMSTRING(len)` | PASS | planned |
| | `SAVE_JSON(...)` | PASS | planned |
| **Trigger** | `ALIAS.F := 1` (trigger write) | PASS | planned |

## Notes

- `MEDIA` (German "Mittelwert" = average, not median) — not found in pilot DDFs but documented in DeviceLib.pdf
- `ARRAY.MAX`, `ARRAY.MIN` — not found in pilot DDFs
- `RFORMULA` — inline in `*ITEM`, used for write-back inverse mapping
