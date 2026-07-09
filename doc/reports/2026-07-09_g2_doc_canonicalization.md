# G2 Doc Canonicalization Report

Date: 2026-07-09

## Scope

G2 from `doc/work_orders/active/codex_github_publication_work_order.md` reorganized the documentation tree and established canonical spec paths.

## Canonical Files

| Area | New canonical path | Previous path |
| --- | --- | --- |
| Optical engine spec | `doc/engine_spec.md` | `doc/optical_engine_spec_v2_3.md` |
| Workbench UI spec | `doc/ui_spec.md` | `doc/optics_workbench_ui_spec_v0_3.md` |

## Work Order Classification

| Status | File | Rationale |
| --- | --- | --- |
| active | `doc/work_orders/active/codex_github_publication_work_order.md` | G1 complete; G2-G5 remain in this publication sequence. |
| active | `doc/work_orders/active/codex_p0-7_performance_work_order.md` | Performance follow-up work remains actionable. |
| done | `doc/work_orders/done/codex_engine_api_addendum_work_order.md` | A0-A3 are completed and reported in `doc/reports/engine_api_addendum_a0_a3_report.md`. |
| done | `doc/work_orders/done/codex_ui_i18n_work_order.md` | U1-U5 are completed and reported in `doc/reports/implementation_status_v2_3_ui_i18n.md`. |
| done | `doc/work_orders/done/codex_ui_phase2_work_order.md` | P2-0 through P2-5 are completed and reported in `doc/reports/ui_phase2_acceptance_report.md`. |

## Archive

Moved old specs and duplicated glossary seed files to `doc/archive/`:

- `doc/archive/optical_engine_spec_v2.md`
- `doc/archive/optical_engine_spec_v2_1.md`
- `doc/archive/optics_workbench_ui_spec_v0_2.md`
- `doc/archive/glossary.ja.json`
- `doc/archive/glossary.en.json`

The glossary source of truth is now explicitly documented as:

```text
apps/workbench-ui/src/i18n/glossary/
```

## Active Path Updates

Updated active work-order references so active instructions point to the canonical spec paths:

- `doc/work_orders/active/codex_github_publication_work_order.md`
  - replaced the old example path `doc/optical_engine_spec_v2_3.md` with `doc/engine_spec.md`
  - added `doc/ui_spec.md` as the companion canonical UI path

No remaining old canonical spec path references were found under `doc/work_orders/active/`.

## Resulting Tree

```text
doc/
  README.md
  engine_spec.md
  ui_spec.md
  images/
  work_orders/
    active/
      codex_github_publication_work_order.md
      codex_p0-7_performance_work_order.md
    done/
      codex_engine_api_addendum_work_order.md
      codex_ui_i18n_work_order.md
      codex_ui_phase2_work_order.md
  reports/
    2026-07-09_g1_publication_clean_scan.md
    2026-07-09_g2_doc_canonicalization.md
    engine_api_addendum_a0_a3_report.md
    implementation_status_phase1_8.md
    implementation_status_v2_1.md
    implementation_status_v2_3_ui_i18n.md
    ui_phase2_acceptance_report.md
  archive/
    glossary.en.json
    glossary.ja.json
    optical_engine_spec_v2.md
    optical_engine_spec_v2_1.md
    optics_workbench_ui_spec_v0_2.md
```

## Notes

- Historical reports still contain some references to their original pre-G2 file paths. They were left intact where they describe past work.
- `doc/archive/` is explicitly non-canonical and should not be used as an implementation target.
