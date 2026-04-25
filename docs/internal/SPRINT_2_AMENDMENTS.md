# Sprint 2 PRD — Amendments

**Date:** 2026-04-25
**Context:** Pre-Day-1 review of Sprint 2 PRD against Sprint 0/1 reality.
**Decision authority:** Martin Mair (ekon GmbH)

---

## 1. AST → CSV Serializer (New Module)

**Finding:** PRD §6.5 says "Serialize: AST → CSV bytes via the Sprint-0 serializer (which already exists for signing canonicalization)." This module does NOT exist. Sprint 0 signing uses raw file bytes, not AST serialization.

**Decision:** New module `ddf_toolkit.serializer` is Day-1 priority. Sprint grows to 16 working days.

**Test criterion:** `parse(serialize(parse(pilot.csv)))` produces structurally identical AST (`raw_source` excluded).

## 2. Template Contract: `build_formulas()` Removed

**Finding:** PRD §6.3 has `build_formulas() -> list[FormulaDef]` in the template contract. But Sprint 0 Amendments §2.6 established: there is no `*FORMULA` section. Formulas are inline in `*WRITE` and `*ITEM`.

**Decision:** Template contract has only `build_items()` and `build_writes()`. Items carry `wformula`/`rformula`, Writes carry `formula`.

## 3. Round-Trip Structural Compare

**Decision:** `ast_equal()` function ignores `raw_source` when comparing ASTs. All other fields must match.

## 4. Group Split for >25 Same-Domain Items

**Decision:** If a group exceeds 25 items and all are same domain, split by HA area. Fallback: numeric split (Group 1: items 1-25, Group 2: items 26-50). Document in `docs/bridge.md`.

## 5. HA Service-Call DDF Pattern

**Decision:** Joe designs, Martin provides guardrails:
- `*GENERAL` Block 2: `DOMAIN` = HA base URL, `AUTHENTIFICATION` = `PASSWORD` with `*CONFIG` field for Bearer token
- `*WRITE` FORMULA: `POST /api/services/<domain>/<service>` with JSON body via `CONCAT()`
- Response: `HTTP_CODE` + `HTTP_DATA`, same pattern as pilot DDFs
- Pattern established with `switch` template first, canonized in `docs/bridge.md` BEFORE template 2 starts
- No inconsistent idioms between templates

## 6. Device-ID Schema for HA-Bridge DDFs

**Format:** `0x0DFA00<8-hex-hash-of-(manufacturer,model,schema)>0100`
- `0xFA` prefix marks "HA-Bridge-generated"
- Prevents collision with DeviceLib portal entries
- Document in `docs/bridge.md`

## 7. Anonymizer Determinism

**Decision:** Per-snapshot determinism. No global state. Same input → same output.

## 8. Hostinger HA Access

**Status:** Martin sets up HA in Docker on Hostinger. Credentials via GitHub Secrets (`HA_TEST_URL`, `HA_TEST_TOKEN`). May not be ready until Day 5. Sprint proceeds in snapshot mode until then.

## 9. Stretch Gate: Day 12 (not Day 10)

**Decision:** Stretch gate moved from Day 10 to Day 12. If all 10 templates + pipeline green by Day 12 → 3 days hardware stretch. Otherwise clean main delivery.

**Fallback:** If Tier-3 templates (climate, media_player, vacuum) struggle at Day 14 → ship 8 clean templates, defer remaining 2 to Sprint 3.

## 10. Snapshot Commit Policy

No snapshot committed to the repo without Martin's explicit OK. Anonymizer has `--verify` mode checking all strings against an allowlist.

---

*This document supplements the Sprint 2 PRD. In case of conflict, this document takes precedence.*
