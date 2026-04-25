# Architecture

## Module Map

```
ddf-toolkit
├── cli.py              # Typer-based CLI entry point
├── parser/             # DDF CSV → typed AST
│   ├── lexer.py        # CSV tokenization, encoding detection
│   ├── parser.py       # Section parsing, AST construction
│   └── ast.py          # Frozen dataclasses for all DDF sections
├── linter/             # Rule-based validation
│   ├── rules.py        # Rule registry (DDF001-DDF010)
│   └── reporter.py     # Finding dataclass, JSON/text output
├── formula/            # DDF script-language engine
│   ├── lexer.py        # Formula tokenizer
│   ├── parser.py       # Formula AST (Sprint 0: parse-only)
│   ├── evaluator.py    # Sprint 1: tree-walking interpreter
│   └── operators/      # One file per operator family
├── signing/            # ECDSA-SHA384
│   ├── keys.py         # Test keypair generation
│   ├── sign.py         # Sign DDF bytes
│   └── verify.py       # Verify signature
├── simulator/          # Sprint 1: HAR-based mock simulation
└── golden/             # Sprint 1: golden-file comparison
```

## Data Flow

```
DDF CSV file
    │
    ▼
┌─────────┐     ┌─────────┐     ┌─────────┐
│  Lexer   │────▶│ Parser  │────▶│  DDF    │
│ (CSV→    │     │ (rows→  │     │  AST    │
│  rows)   │     ���  AST)   │     │         │
└─────────┘     └─────────┘     └────┬────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              ┌─────────┐     ┌──────────┐     ┌─────────┐
              │ Linter  │     │ Formula  │     │ Signing │
              │ (rules) │     │ (parse)  │     │ (ECDSA) │
              └─────────┘     └──────────┘     └─────────┘
```

## Key Design Decisions

### AST follows DDF reality, not PRD prediction

See [SPRINT_0_AMENDMENTS.md](internal/SPRINT_0_AMENDMENTS.md) Section 2 for the six
structural differences between the PRD's predicted AST and the actual DDF file format.

Key findings:
- `*SIGNATURE` is the first section
- `*GENERAL` appears twice (metadata + connection params)
- `*ARGS` are inline under `*WRITE`, not top-level
- `*READ` is empty; all logic runs via `*WRITE` formulas with trigger flags
- Formulas are inline in `*WRITE` and `*ITEM`, not a separate section

### Formula engine is a scripting language

DDF formulas are not pure expressions — they are an imperative scripting language with
assignments (`:=`), block IF/THEN/ELSE/ENDIF, side effects, and 25+ built-in functions.
Sprint 0 parses and validates; Sprint 1 adds execution.
