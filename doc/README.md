# Documentation Index

This directory is the canonical documentation home for the optics engine and workbench UI.

## Canonical Specs

| Area | Canonical file | Current version |
| --- | --- | --- |
| Optical engine | `doc/engine_spec.md` | v2.3 |
| Workbench UI | `doc/ui_spec.md` | v0.3 |

Use these two files as the source of truth for implementation and review. Older specs under `doc/archive/` are historical references only and must not be used as active implementation targets.

## Work Orders

Only work orders in `doc/work_orders/active/` are actionable. Work orders in `doc/work_orders/done/` are retained as completion records and should not be re-executed unless a new active order explicitly revives them.

| Status | File | Notes |
| --- | --- | --- |
| active | `doc/work_orders/active/codex_p0-7_performance_work_order.md` | Performance and optimization follow-up work. |
| done | `doc/work_orders/done/codex_engine_api_addendum_work_order.md` | A0-A3 completed; see `doc/reports/engine_api_addendum_a0_a3_report.md`. |
| done | `doc/work_orders/done/codex_ui_i18n_work_order.md` | U1-U5 completed; see `doc/reports/implementation_status_v2_3_ui_i18n.md`. |
| done | `doc/work_orders/done/codex_ui_phase2_work_order.md` | P2-0 through P2-5 completed; see `doc/reports/ui_phase2_acceptance_report.md`. |

## Reports

Implementation reports live in `doc/reports/`.

New reports should use:

```text
YYYY-MM-DD_<task-number>_<subject>.md
```

Existing pre-publication reports that predate this convention are retained in `doc/reports/` for traceability.

## Archive

`doc/archive/` contains old specs and duplicated seed assets. Do not add new active work there, and do not cite archive files as the current implementation target.

The glossary source of truth is the UI implementation directory:

```text
apps/workbench-ui/src/i18n/glossary/
```

The archived `doc/archive/glossary.*.json` files are retained only as the original seed copies.
