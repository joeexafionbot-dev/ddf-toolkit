# DDF Schema Reference

Canonical reference for DDF (Device Definition File) sections and their fields.
Source: `DeviceLib.pdf` + pilot DDF analysis.

> Items marked `// AMBIGUOUS` need confirmation from Martin.

## File Format

- CSV with `;` delimiter
- Encoding: UTF-8 or CP1252 (auto-detected via BOM + chardet)
- Lines starting with `#` are comments (skipped by parser)
- Sections start with `*SECTION_NAME`

## Sections

### `*SIGNATURE`

First section in signed DDFs. Contains the cryptographic signature.

| Field | Type | Description |
|-------|------|-------------|
| SIGN_ALGO | string | Signature algorithm (e.g., `ECDSA-SHA384`) |
| SIGN_DATE | datetime | When the file was signed |
| FILE_VERDATE | string | File version hash + date |
| SIGNATURE | string | Base64-encoded signature |

### `*GENERAL` (Block 1 — Device Metadata)

| Field | Type | Description |
|-------|------|-------------|
| DEVICE | string | Device name |
| MANUFACTURER | string | Manufacturer name |
| TYPE | string | Device type (e.g., `Gateway`, `Air conditioner`) |
| PROTOCOL | string | Protocol (e.g., `REST-API (DDF)`) |
| MODEL_NR | string | Model number |
| VERSION_NR | string | Version number |
| ID | hex string | Unique device identifier (e.g., `0x0D00007700010100`) |
| MIN_CONTROL_VERSION | string | Minimum controller firmware version |
| TIMESTAMP | datetime | Last modification timestamp |
| VERSION_INFO | string | Optional version info |
| VERSION_USER | string | User who created the version |
| REVISION | string | Revision hash + date |

### `*GENERAL` (Block 2 — Connection & Auth)

| Field | Type | Description |
|-------|------|-------------|
| CONNECTION | enum | Connection type: `DOMAIN`, `DEFDOMAIN`, `IPADDRESS`, etc. |
| AUTHENTIFICATION | enum | Auth method: `NONE`, `PASSWORD`, `OAUTH_DEVICE_FLOW`, etc. |
| DOMAIN | string | Primary API domain |
| SLAVESMAX | int | Maximum number of sub-devices |
| DEBUGPORT | int | Debug port (recommended: 8500-8600) |
| (dynamic fields) | string | Runtime state: ACCESSTOKEN, EXPIRESIN, etc. |

> Note: Spelling is `AUTHENTIFICATION` (not `AUTHENTICATION`) per DDF convention.

### `*COMMAND`

| Column | Type | Description |
|--------|------|-------------|
| ID | int | Command index |
| ALIAS | string | Command name |
| FORMULA | string | Script to execute when command is triggered |

### `*CONFIG`

| Column | Type | Description |
|--------|------|-------------|
| ID | int | Config field index |
| ALIAS | string | Config field name (e.g., `TENANTID`, `CLIENTID`) |

### `*READ`

| Column | Type | Description |
|--------|------|-------------|
| ALIAS | string | Read command name |
| METHOD | string | HTTP method |
| URL | string | Endpoint URL |
| DATATYPE | string | Response data type |
| POLLING | int | Polling interval in ms |

> Note: `*READ` is empty in both pilot DDFs. All data fetching is done via `*WRITE` with trigger flags.

### `*WRITE`

| Column | Type | Description |
|--------|------|-------------|
| ALIAS | string | Write command name |
| METHOD | string | HTTP method (GET, POST, PATCH, etc.) |
| URL | string | Endpoint URL (may be empty if built from ARGS) |
| DATATYPE | string | `JSON`, `X-WWW-FORM-URLENCODED`, etc. |
| FORMULA | string | Script executed after HTTP response |

#### Inline `*ARGS` (nested under `*WRITE`)

| Column | Type | Description |
|--------|------|-------------|
| METHOD | string | Always `ARGS` |
| ALIAS | string | Parent WRITE alias |
| TYPE | string | Arg type: `url`, `arg`, `data`, `header` |
| NAME | string | Parameter name |
| VALUE | string | Static value |
| ITEM | string | Dynamic value reference (e.g., `$.CONFIG.1`) |
| FORMAT | string | Format string (e.g., `Bearer %s`) |

### `*ITEM`

| Column | Type | Description |
|--------|------|-------------|
| ALIAS | string | Item identifier |
| NAME | string | Human-readable name |
| ID | int | Numeric item ID (referenced as `X.{ID}` in formulas) |
| VISIBILITY | string | `HIDDEN` or empty |
| UNIT | string | Unit of measurement |
| TYPE | string | Data type |
| DEFAULT | string | Default value |
| WFORMULA | string | Write formula (triggered on value change) |
| RFORMULA | string | Read formula (periodic, based on POLLING) |
| POLLING | int | Polling interval in ms |

### `*GROUP`

| Column | Type | Description |
|--------|------|-------------|
| ID | int | Group index |
| ALIAS | string | Group identifier |
| NAME | string | Display name |

> Note: Column order varies between DDFs (ID;ALIAS;NAME vs. ALIAS;ID;NAME).

### `*OBJECT`

UI object definitions linking items to display widgets.

| Column | Type | Description |
|--------|------|-------------|
| GROUP | int | Parent group ID |
| ID | int | Object index within group |
| ALIAS | string | Display name |
| TYPE | int | Widget type (1=bool, 2=float, 3=string, 4=gauge, 5=link, 104=slider) |
| ENUM | int | Number of enum values |
| ENUMTEXT | string | Comma-separated enum labels |
| ENUMVAL | string | Comma-separated enum values |
| MIN | float | Minimum value |
| MAX | float | Maximum value |
| IOTYPE | int | I/O direction |
| DIGITS | int | Decimal digits |
| ITEMID | int | Referenced item ID |
| UNIT | string | Display unit |
| ALARM | string | Alarm condition |
| ALARMVAL | string | Alarm threshold |
| ALARMTIME | int | Alarm duration |
| OUTTYPE | int | Output type |
| CMDITEMID | int | Command item ID |
| COMMAND | string | Command text |
| COMMANDENUM | string | Command enum values |
| COMMANDVAL | string | Command trigger values |
| VIEWTYPE | int | View type (0=normal, 1=detail, 2=hidden) |
| LOG | int | Logging enabled (0/1) |
