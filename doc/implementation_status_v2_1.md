# Optical Engine v2.1 Implementation Status

## Summary

Engine-side v2.1 support has been implemented and verified for the current Python library and FastAPI wrapper.

Verification result:

```text
47 passed in 0.84s
```

Command:

```powershell
<python> -B -m pytest
```

## Implemented v2.1 Items

- `GET /v1/health`
- `GET /v1/meta`
- `GET /v1/artifacts/{category}/{id}`
- `POST /v1/trace/reverse`
- `POST /v1/analysis/ray-fan`
- `POST /v1/analysis/longitudinal-aberration`
- `POST /v1/analysis/distortion`
- `POST /v1/solve/best-focus`
- `POST /v1/materials/refractive-index`
- `image_plane_policy`
  - `fixed_sensor`
  - `paraxial_image`
  - `best_focus_rms`
  - `best_focus_mtf`
  - `best_focus_merit`
  - `custom_offset`
  - `sweep`
- `image_plane_policy.apply_to`
  - `evaluation_plane`
  - `focus_group`
  - `report_only`
  - `sensor_surface` remains intentionally client-side write-back, per spec.
- Artifact TTL store and JSON artifact retrieval.
- `metadata.evaluation_plane` on image-plane-dependent analysis responses.
- `profiling: true` trace metadata.
- v2.1 Cassegrain corrected values regression.
- Material models:
  - `constant`
  - `nd_vd`
  - `sellmeier`
  - `catalog` with built-in `N-BK7` / `BK7`
  - `custom_table`

## API Coverage

All endpoints listed in `doc/optical_engine_spec_v2_1.md` section 26.3 are now routed in `optics_engine/api/main.py`.

HTTP smoke coverage uses FastAPI `TestClient` for:

- health
- meta
- system register
- spot analysis with `image_plane_policy`
- artifact fetch
- material refractive index

## Known Future Extensions

The following are still intentionally outside the implemented v2.1 build, because the spec marks or treats them as future/deeper extensions rather than current API-contract blockers:

- Polygon aperture blade geometry.
- Non-angular field source types.
- Diffraction PSF / wavefront FFT.
- Async jobs / persistent external artifact store.
- Full material catalog database beyond built-in `N-BK7` / `BK7`.
- High-performance vectorized/Numba batch kernel work from `doc/codex_performance_work_order.md`.

## Changed Areas

- `optics_engine/api/main.py`
- `optics_engine/artifacts.py`
- `optics_engine/metadata.py`
- `optics_engine/image_plane.py`
- `optics_engine/aberrations.py`
- `optics_engine/tracing.py`
- `optics_engine/models.py`
- `optics_engine/__init__.py`
- `tests/test_engine_v2_1.py`
- `pyproject.toml`
