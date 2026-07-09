# <REPO_NAME> — Optics Workbench

An educational optical simulation engine and web workbench for photographic lenses, binoculars, and telescopes.

**Status: work in progress.** APIs and specs are evolving.

[English](#overview) | [日本語](#日本語)

---

## Overview

This project combines:

- **Optics engine** (Python) — 3D sequential ray tracing on a +X optical axis: spherical/aspheric surfaces, mirrors, stops, ideal thin lenses; paraxial (y-nu) analysis; ray aiming; spot / ray fan / distortion / field curvature / chromatic aberration; geometric PSF/MTF; relative illumination; afocal (visual instrument) evaluation with exit pupil, eye relief, and angular MTF. Exposed as a stateless HTTP API for UIs and external optimizers.
- **Workbench UI** (React + TypeScript + Carbon) — surface table editing, layout view, analysis charts, snapshots and comparison. Fully bilingual (Japanese / English) with a built-in optics glossary and three-tier help (term toggletips, help drawer, structured error explanations).

Design goals, in order: **make optics visible for learners**, enable quick design studies, and serve as an evaluation backend for external optimization (DLS-friendly operand/residual API).

### Screenshots

<!-- TODO(codex): replace with actual sanitized screenshots under doc/images/ -->
| Workbench (ja) | Workbench (en) | Help drawer |
|---|---|---|
| ![ja](doc/images/workbench-ja.png) | ![en](doc/images/workbench-en.png) | ![help](doc/images/help-drawer.png) |

### Quick start

Requirements: Python 3.12+, Node 20+.

```bash
# Engine (HTTP API)
# TODO(codex): replace with the actual install & run commands
pip install -e .
python -m optics_engine.api.main   # serves http://localhost:8000

# Workbench UI
npm ci
npm run dev                        # opens the workbench against the local engine
```

Run the test suites:

```bash
pytest -q          # engine tests incl. golden reference designs
npm run ci         # UI build + i18n checks + glossary coverage
```

### Documentation

Specifications are maintained in Japanese as the source of truth:

- [`doc/engine_spec.md`](doc/engine_spec.md) — engine requirements & technical spec (current: v2.3)
- [`doc/ui_spec.md`](doc/ui_spec.md) — workbench UI spec (current: v0.3)
- [`AGENTS.md`](AGENTS.md) — rules for AI coding agents working on this repo

### Project status

<!-- TODO(codex): keep this table current -->
| Area | Status |
|---|---|
| Engine core (trace, paraxial, aberrations, PSF/MTF, afocal) | Implemented (MVP, Phases 1–8) |
| Engine performance (vectorized kernel, ray-aiming cache) | In progress |
| Engine optimization API (operands, jacobian) | Planned |
| UI Phase 1 (editing, layout, paraxial, preview) + i18n/help | Implemented |
| UI Phase 2 (analysis views, best focus, snapshots/compare) | In progress |
| UI Phases 3–4 (design ops, visual instruments) | Planned |

### License

Apache License 2.0 — see [LICENSE](LICENSE).

---

## 日本語

写真レンズ・双眼鏡・望遠鏡を対象とした、教育目的の光学シミュレーションエンジンとWeb Workbenchです。光線追跡・収差解析・PSF/MTF・視覚系評価をステートレスHTTP APIとして提供し、UIは日英対応・光学用語集・3階層ヘルプを内蔵しています。仕様書（正本）は日本語で `doc/` 以下にあります。開発中のため、APIと仕様は変更されることがあります。
