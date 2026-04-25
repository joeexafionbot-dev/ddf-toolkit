# Formula Operator Coverage

Complete operator/function inventory from DeviceLib.pdf Section 2.6.
Sprint 1 implements execution for all pilot-DDF operators.

## Control Flow

| Operator | Sprint 0 (Parse) | Sprint 1 (Execute) | Source |
|----------|:-:|:-:|--------|
| `IF / THEN / ELSE / ENDIF` | PASS | DONE | Pilot DDFs + DeviceLib p.24 |
| `ELSE IF` | PASS | DONE | Pilot DDFs |
| `SWITCH / CASE / DEFAULT / ENDSWITCH` | PASS | DONE | DeviceLib p.25 |
| `FOR / TO / BY / DO / ENDFOR` | PASS | DONE | DeviceLib p.25 |

## Assignment

| Operator | Sprint 0 (Parse) | Sprint 1 (Execute) | Source |
|----------|:-:|:-:|--------|
| `:=` | PASS | DONE | Pilot DDFs |

## Comparison

| Operator | Sprint 0 (Parse) | Sprint 1 (Execute) |
|----------|:-:|:-:|
| `==`, `!=`, `<`, `>`, `<=`, `>=` | PASS | DONE |

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
| `+`, `-`, `*`, `/` | PASS | DONE |
| `^` (power) | PASS | DONE |

## Variable Access

| Pattern | Sprint 0 (Parse) | Sprint 1 (Execute) |
|---------|:-:|:-:|
| `X.{ID}` | PASS | DONE |
| `ITEM.ALIAS` | PASS | DONE |
| `$.GPARAM.*`, `$.SYS.TIME`, `$.CONFIG.*`, `$.PARAM.*` | PASS | DONE |
| `$.SLAVE.x.yyy` | PASS | DONE |
| `ALIAS.VALUE.path[i].field` | PASS | DONE |
| `ALIAS.HTTP_CODE`, `ALIAS.HTTP_DATA`, `ALIAS.URL` | PASS | DONE |
| `ALIAS.ARRAY.LEN/MAX/MIN/MEDIA.path` | PASS | DONE |
| `ALIAS.ASLIST.path[].field` | PASS | DONE |
| `ALIAS.EXIST.path` | PASS | DONE |
| `ALIAS.F` (trigger), `ALIAS.T`, `ALIAS.Q`, `ALIAS.L`, `ALIAS.P` | PASS | DONE |

## Built-in Functions

### Date/Time

| Function | Sprint 0 | Sprint 1 | Source |
|----------|:-:|:-:|--------|
| `DATE_MONTH/YEAR/WDAY/YDAY/HOUR/MIN/SEC/DAY(time)` | PASS | DONE | DeviceLib p.26 |
| `TIME_FROM_YDAY(year, yearday)` | PASS | DONE | DeviceLib p.26 |
| `TIME_FROM_DATE(y, m, d [,h, min, sec])` | PASS | DONE | DeviceLib p.26 |
| `TIMEFROMISO8601(isostring)` | PASS | DONE | DeviceLib p.26 |
| `ISO8601(time, type)` | PASS | DONE | DeviceLib p.27 |
| `DATE(time)` | PASS | DONE | Pilot DDFs |

### Math

| Function | Sprint 0 | Sprint 1 | Source |
|----------|:-:|:-:|--------|
| `LOG(value, base)` | PASS | DONE | DeviceLib p.26 |
| `DEC(val)` / `DEC(val, div)` | PASS | DONE | DeviceLib p.26 |
| `MOD(val, div)` | PASS | DONE | DeviceLib p.26 |
| `ROUND(val)` / `ROUND(val, div)` | PASS | DONE | DeviceLib p.26 |
| `SINEFROMTIME(freq, amp, phase)` | PASS | DONE | DeviceLib p.26 |

### String

| Function | Sprint 0 | Sprint 1 | Source |
|----------|:-:|:-:|--------|
| `LEN(str)` | PASS | DONE | Pilot DDFs |
| `ISEQUAL(s1, s2 [,len])` | PASS | DONE | Pilot DDFs |
| `SUBSTRING(str, start [,len])` | PASS | DONE | Pilot DDFs |
| `CONCAT(s1, s2, ...)` | PASS | DONE | Pilot DDFs |
| `DECIMAL_TO_STRING(number)` | PASS | DONE | Pilot DDFs |
| `FLOAT_TO_STRING(number)` | PASS | DONE | DeviceLib p.27 |
| `REPLACEWITHASCII(text, search, ascii)` | PASS | DONE | Pilot DDFs |
| `STRING_TO_NUMBER(str, start, len, type)` | PASS | DONE | DeviceLib p.27 |
| `HEXSTRING_TO_NUMBER(str, start, len, type)` | PASS | DONE | DeviceLib p.27 |

### System

| Function | Sprint 0 | Sprint 1 | Source |
|----------|:-:|:-:|--------|
| `DEBUG(var1, var2, ...)` | PASS | DONE | Pilot DDFs |
| `SYSTEMINFO(xxx)` | PASS | DONE | Pilot DDFs |
| `RANDOMSTRING(len)` | PASS | DONE | Pilot DDFs |
| `SAVE_JSON(...)` | PASS | DONE | Pilot DDFs |

### Advanced

| Function | Sprint 0 | Sprint 1 | Source |
|----------|:-:|:-:|--------|
| `SETVALUE(prefix, suffix, index, value, ...)` | PASS | DONE | DeviceLib p.27 |
| `SETVALUES(prefix, suffix, index, blocks, value, ...)` | PASS | DONE | DeviceLib p.27 |
| `JSONGETVALUEFROMARRAY(...)` | PASS | DONE | DeviceLib p.28 |
| `PID(instance, soll, ist, P, I, D, N)` | PASS | DONE | DeviceLib p.28 |
| `FUNCTION(slave, target, op, source, addr, count)` | PASS | DONE | DeviceLib p.10 |

## Notes

- `ARRAY.MEDIA` = average (German "Mittelwert"), NOT median
- Function params must be variables, not literal numbers (parser limitation with decimals)
- Comments: `/* ... */` (multi-line)
- No spaces allowed inside function calls
