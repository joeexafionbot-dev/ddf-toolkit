# Formula Operator Coverage

Complete operator/function inventory from DeviceLib.pdf Section 2.6.
Sprint 0 parses all tokens; execution is Sprint 1.

## Control Flow

| Operator | Sprint 0 (Parse) | Sprint 1 (Execute) | Source |
|----------|:-:|:-:|--------|
| `IF / THEN / ELSE / ENDIF` | PASS | planned | Pilot DDFs + DeviceLib p.24 |
| `ELSE IF` | PASS | planned | Pilot DDFs |
| `SWITCH / CASE / DEFAULT / ENDSWITCH` | PASS | planned | DeviceLib p.25 |
| `FOR / TO / BY / DO / ENDFOR` | PASS | planned | DeviceLib p.25 |

## Assignment

| Operator | Sprint 0 (Parse) | Sprint 1 (Execute) | Source |
|----------|:-:|:-:|--------|
| `:=` | PASS | planned | Pilot DDFs |

## Comparison

| Operator | Sprint 0 (Parse) | Sprint 1 (Execute) |
|----------|:-:|:-:|
| `==`, `!=`, `<`, `>`, `<=`, `>=` | PASS | planned |

## Logical / Bitwise

| Operator | Meaning | Sprint 0 (Parse) | Sprint 1 (Execute) | Notes |
|----------|---------|:-:|:-:|-------|
| `&&` | Logical AND | PASS | Sprint 1 | Used in pilots |
| `\|\|` | Logical OR | PASS | Sprint 2 | Not in pilots |
| `!` / `NOT` | Logical NOT | PASS | Sprint 2 | Not in pilots |
| `&!` | AND NOT | PASS | Sprint 2 | Not in pilots |
| `\|` | Bitwise OR | PASS | Sprint 2 | Not in pilots |
| `&` | Bitwise AND | PASS | Sprint 2 | Not in pilots |
| `&~` | Bitwise AND NOT | PASS | Sprint 2 | Not in pilots |
| `>>` | Shift right | PASS | Sprint 2 | Not in pilots |
| `<<` | Shift left | PASS | Sprint 2 | Not in pilots |

## Arithmetic

| Operator | Sprint 0 (Parse) | Sprint 1 (Execute) |
|----------|:-:|:-:|
| `+`, `-`, `*`, `/` | PASS | planned |
| `^` (power) | PASS | planned |

## Variable Access

| Pattern | Sprint 0 (Parse) | Sprint 1 (Execute) |
|---------|:-:|:-:|
| `X.{ID}` | PASS | planned |
| `ITEM.ALIAS` | PASS | planned |
| `$.GPARAM.*`, `$.SYS.TIME`, `$.CONFIG.*`, `$.PARAM.*` | PASS | planned |
| `$.SLAVE.x.yyy` | PASS | planned |
| `ALIAS.VALUE.path[i].field` | PASS | planned |
| `ALIAS.HTTP_CODE`, `ALIAS.HTTP_DATA`, `ALIAS.URL` | PASS | planned |
| `ALIAS.ARRAY.LEN/MAX/MIN/MEDIA.path` | PASS | planned |
| `ALIAS.ASLIST.path[].field` | PASS | planned |
| `ALIAS.EXIST.path` | PASS | planned |
| `ALIAS.F` (trigger), `ALIAS.T`, `ALIAS.Q`, `ALIAS.L`, `ALIAS.P` | PASS | planned |

## Built-in Functions

### Date/Time

| Function | Sprint 0 | Sprint 1 | Source |
|----------|:-:|:-:|--------|
| `DATE_MONTH/YEAR/WDAY/YDAY/HOUR/MIN/SEC/DAY(time)` | PASS | planned | DeviceLib p.26 |
| `TIME_FROM_YDAY(year, yearday)` | PASS | planned | DeviceLib p.26 |
| `TIME_FROM_DATE(y, m, d [,h, min, sec])` | PASS | planned | DeviceLib p.26 |
| `TIMEFROMISO8601(isostring)` | PASS | planned | DeviceLib p.26 |
| `ISO8601(time, type)` | PASS | planned | DeviceLib p.27 |
| `DATE(time)` | PASS | planned | Pilot DDFs |

### Math

| Function | Sprint 0 | Sprint 1 | Source |
|----------|:-:|:-:|--------|
| `LOG(value, base)` | PASS | planned | DeviceLib p.26 |
| `DEC(val)` / `DEC(val, div)` | PASS | planned | DeviceLib p.26 |
| `MOD(val, div)` | PASS | planned | DeviceLib p.26 |
| `ROUND(val)` / `ROUND(val, div)` | PASS | planned | DeviceLib p.26 |
| `SINEFROMTIME(freq, amp, phase)` | PASS | planned | DeviceLib p.26 |

### String

| Function | Sprint 0 | Sprint 1 | Source |
|----------|:-:|:-:|--------|
| `LEN(str)` | PASS | planned | Pilot DDFs |
| `ISEQUAL(s1, s2 [,len])` | PASS | planned | Pilot DDFs |
| `SUBSTRING(str, start [,len])` | PASS | planned | Pilot DDFs |
| `CONCAT(s1, s2, ...)` | PASS | planned | Pilot DDFs |
| `DECIMAL_TO_STRING(number)` | PASS | planned | Pilot DDFs |
| `FLOAT_TO_STRING(number)` | PASS | planned | DeviceLib p.27 |
| `REPLACEWITHASCII(text, search, ascii)` | PASS | planned | Pilot DDFs |
| `STRING_TO_NUMBER(str, start, len, type)` | PASS | planned | DeviceLib p.27 |
| `HEXSTRING_TO_NUMBER(str, start, len, type)` | PASS | planned | DeviceLib p.27 |

### System

| Function | Sprint 0 | Sprint 1 | Source |
|----------|:-:|:-:|--------|
| `DEBUG(var1, var2, ...)` | PASS | planned | Pilot DDFs |
| `SYSTEMINFO(xxx)` | PASS | planned | Pilot DDFs |
| `RANDOMSTRING(len)` | PASS | planned | Pilot DDFs |
| `SAVE_JSON(...)` | PASS | planned | Pilot DDFs |

### Advanced

| Function | Sprint 0 | Sprint 1 | Source |
|----------|:-:|:-:|--------|
| `SETVALUE(prefix, suffix, index, value, ...)` | PASS | planned | DeviceLib p.27 |
| `SETVALUES(prefix, suffix, index, blocks, value, ...)` | PASS | planned | DeviceLib p.27 |
| `JSONGETVALUEFROMARRAY(...)` | PASS | planned | DeviceLib p.28 |
| `PID(instance, soll, ist, P, I, D, N)` | PASS | planned | DeviceLib p.28 |
| `FUNCTION(slave, target, op, source, addr, count)` | PASS | planned | DeviceLib p.10 |

## Notes

- `ARRAY.MEDIA` = average (German "Mittelwert"), NOT median
- Function params must be variables, not literal numbers (parser limitation with decimals)
- Comments: `/* ... */` (multi-line)
- No spaces allowed inside function calls
