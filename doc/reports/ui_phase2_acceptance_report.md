# UI Phase 2 Acceptance Report

Created: 2026-07-09

## Scope

This report closes UI Phase 2 work items P2-0 through P2-5 from `doc/codex_ui_phase2_work_order.md`.

Primary references:

- UI spec: `doc/optics_workbench_ui_spec_v0_3.md`
- Phase 2 work order: `doc/codex_ui_phase2_work_order.md`
- Engine/API handoff: `doc/engine_api_addendum_a0_a3_report.md`

## Phase 2 Status

| Task | Scope | Status | Commit |
|---|---|---|---|
| P2-0 | Toggletip E2E, SVG export readback, i18n CI gaps | Done | `ce1957d` |
| P2-1 | Analysis condition editor and dirty/evaluated-field flow | Done | `b129679` |
| P2-2 | Analysis chart views and P003 achromat preset | Done | `ae1aca5` |
| P2-3 | Image plane policy UI, focus curve, sensor write-back, P006 disable | Done | `a83529a` |
| P2-4 | Snapshot artifact embedding and two-condition compare | Done with noted export limitation | `acfdfd5` |
| P2-5 | Acceptance report, coverage status, supplement review list, responsiveness memo | Done | this task |

## Acceptance Matrix

| Requirement | Status | Evidence |
|---|---|---|
| Field, wavelength, and ray sampling editing | Done | Playwright `analysis condition edits mark dirty and rerun preview with updated results` |
| Dirty/stale state | Done | Same E2E verifies dirty-to-clean transition |
| Evaluated field metadata display | Done | Same E2E checks response metadata fields |
| Ray fan, distortion, field curvature, RI, MTF charts | Done | Playwright `P003 analysis charts render...`; `chart-theme:test` |
| Image plane policy modes and apply target | Done | UI sends `image_plane_policy`; P2-3 E2E covers `best_focus_rms`; engine tests cover mode execution |
| Focus curve and best focus marker | Done | P2-3 E2E checks focus chart and marker |
| Sensor write-back | Done | P2-3 E2E checks updated sensor thickness and `system_dirty` |
| Afocal policy disable | Done | P2-3 E2E checks P006 disabled policy controls |
| Snapshot embeds volatile artifacts | Done for JSON artifacts | P2-4 E2E covers successful artifact fetch and snapshot save |
| Partial snapshot fallback | Done | P2-4 E2E covers `artifact_expired` fallback |
| Two-condition compare | Done | P2-4 E2E covers condition diff and result compare |
| Comparison guard | Done | P2-4 E2E covers field mismatch warning |
| Language-independent snapshots | Done | Snapshot stores raw metric keys; labels resolve with `termLabel` at display time |
| Export | Partial | Single JSON export implemented; zip export remains future work |

## CI Coverage

Latest Phase 2 verification:

```text
npm.cmd run ci: passed
ui:build: passed
i18n:check: ok (120 keys)
i18n:coverage: ok
i18n:test: ok
svg-export-readback: ok
chart-theme:test: ok
Playwright E2E: 6 passed (18.5 s)
```

Known build warning:

- Vite reports dependency-level `"use client" directive ignored` warnings from Carbon and TanStack packages. Build output still succeeds.

## Supplement Review List

The supplement glossary entries are balanced across `ja` and `en`.

Supplement terms:

| Key | Review note |
|---|---|
| `alive` | Ray status label |
| `blocked` | Ray status label |
| `constraint_penalty` | Merit/optimization metric term |
| `geometric_mtf` | Geometric MTF note |
| `missed` | Ray status label |
| `relative_illumination_loss` | RI-related metric term |
| `score` | Generic merit score |

Supplement errors:

| Key | Review note |
|---|---|
| `artifact_not_found` | Artifact lifecycle / snapshot fallback |
| `duplicate_surface_id` | Validation |
| `edge_thickness_below_min` | Validation |
| `image_plane_policy_not_applicable` | P2-3 afocal guard |
| `invalid_asphere_surface` | Validation |
| `invalid_group_range` | Group validation |
| `invalid_tilt_range` | Tilt validation |
| `material_not_found` | Material lookup |
| `min_air_gap` | Merit constraint |
| `mirror_thickness_sign` | Mirror validation |
| `missing_eye_reference` | Afocal validation |
| `missing_focal_length` | Thin lens validation |
| `missing_sensor` | Focal validation |
| `missing_terminal_eye_reference` | Afocal validation |
| `missing_terminal_sensor` | Focal validation |
| `multiple_aperture_stops` | Validation |
| `optics_value_error` | Generic optics error fallback |
| `system_not_found` | System cache/API lifecycle |
| `unknown_focus_group` | Image plane / focus group |
| `unknown_group` | Group validation |
| `unknown_group_surface` | Group validation |
| `unknown_image_plane_policy` | Policy validation |
| `unknown_material` | Material validation |
| `unknown_tilt_target` | Tilt validation |
| `unknown_zoom_group` | Zoom validation |
| `unknown_zoom_position` | Zoom validation |

## Responsiveness Memo

Observed during latest CI:

- Production build completed successfully.
- Playwright E2E suite completed 6 tests in 18.5 seconds on Edge during the final P2-5 verification run.
- Individual mocked UI workflows were approximately 1.0-1.7 seconds each.
- Current chart implementation uses lightweight SVG charts rather than Plotly scattergl. This is adequate for the present MVP data sizes, but the spec-preferred scattergl/WebGL path remains relevant for very large spot clouds or dense fan/MTF overlays.
- Bundle output from the latest build was roughly `498 kB` JavaScript gzip `156 kB`, and `835 kB` CSS gzip `86 kB`.

## Remaining Limitations

| Item | Status |
|---|---|
| Snapshot zip export (`snapshot.json + artifacts/`) | Not implemented |
| PNG export image comparison test | Not implemented |
| Full rich snapshot compare with chart overlays | Partial; current compare is summary/table oriented |
| Raw YAML/JSON advanced editor | Future phase |
| Plotly scattergl/WebGL chart path | Future performance phase |
