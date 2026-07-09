from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass

from .. import (
    analyze_distortion,
    analyze_longitudinal_aberration,
    analyze_ray_fan,
    analyze_chromatic_aberration,
    analyze_field_curvature,
    analyze_geometric_mtf,
    analyze_geometric_psf,
    analyze_ms_image_surface,
    analyze_paraxial,
    analyze_relative_illumination,
    analyze_spot,
    analyze_afocal,
    analyze_angular_mtf,
    analyze_binocular_alignment,
    analyze_exit_pupil,
    analyze_eye_box,
    analyze_telescope,
    analyze_white_mtf,
    analyze_white_psf,
    compile_system,
    evaluate_batch,
    evaluate_system,
    load_system,
    trace_forward,
    trace_reverse,
    validate_system,
)
from ..artifacts import ARTIFACT_STORE, artifact_uri
from ..image_plane import resolve_image_plane_policy
from ..metadata import health_payload, meta_payload
from ..models import Material, OpticsError, StructuredOpticsError

try:
    from fastapi import FastAPI, HTTPException, Request, Response
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
except ImportError as exc:  # pragma: no cover - exercised only without the optional extra
    raise RuntimeError("Install optics-engine[api] to use the HTTP API") from exc


app = FastAPI(title="Optics Engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_detail(code: str, message_en: str, *, params: dict | None = None, severity: str = "error") -> dict:
    return {
        "severity": severity,
        "code": code,
        "params": params or {},
        "message_en": message_en,
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else _error_detail("api_error", str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=detail)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content=_error_detail("optics_value_error", str(exc)))


@app.exception_handler(OpticsError)
async def optics_error_handler(_: Request, exc: OpticsError):
    if isinstance(exc, StructuredOpticsError):
        return JSONResponse(
            status_code=400,
            content=_error_detail(exc.code, exc.message_en, params=exc.params, severity=exc.severity),
        )
    return JSONResponse(status_code=400, content=_error_detail("optics_value_error", str(exc)))


def _jsonable(value):
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _compiled_from_payload(payload: dict):
    from ..system import get_cached_system

    system_id = payload.get("system_id") or payload.get("system_hash")
    if system_id:
        compiled = get_cached_system(str(system_id))
        if compiled is None:
            raise HTTPException(
                status_code=404,
                detail=_error_detail(
                    "system_not_found",
                    "Unknown or expired system_id.",
                    params={"system_id": str(system_id)},
                ),
            )
        return compiled
    system = load_system(payload)
    return compile_system(system)


def _analysis_response(result, evaluation_plane: dict | None = None):
    data = _jsonable(result)
    if evaluation_plane is None:
        return data
    if not isinstance(data, dict):
        data = {"result": data}
    metadata = dict(data.get("metadata", {}))
    metadata["evaluation_plane"] = evaluation_plane
    data["metadata"] = metadata
    return data


def _attach_json_artifact(data: dict, category: str, name: str, payload) -> dict:
    artifact = ARTIFACT_STORE.put(
        category,
        json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8"),
        content_type="application/json",
    )
    artifacts = dict(data.get("artifacts", {}))
    artifacts[name] = artifact_uri(artifact)
    data["artifacts"] = artifacts
    metadata = dict(data.get("metadata", {}))
    artifact_expires = dict(metadata.get("artifact_expires_at", {}))
    artifact_expires[name] = artifact.expires_at
    metadata["artifact_expires_at"] = artifact_expires
    data["metadata"] = metadata
    return data


@app.get("/v1/health")
def health():
    return health_payload()


@app.get("/v1/meta")
def meta():
    return meta_payload()


@app.get("/v1/artifacts/{category}/{id}")
def artifact(category: str, id: str):
    item, status = ARTIFACT_STORE.get_with_status(category, id)
    if status == "expired":
        raise HTTPException(
            status_code=404,
            detail=_error_detail(
                "artifact_expired",
                "Artifact has expired.",
                params={"category": category, "id": id},
            ),
        )
    if status == "not_found" or item is None:
        raise HTTPException(
            status_code=404,
            detail=_error_detail(
                "artifact_not_found",
                "Artifact was not found.",
                params={"category": category, "id": id},
            ),
        )
    return Response(content=item.content, media_type=item.content_type, headers={"X-Artifact-Expires-At": str(item.expires_at)})


@app.post("/v1/systems/validate")
def validate(payload: dict):
    system = load_system(payload)
    return validate_system(system).model_dump(mode="json")


@app.post("/v1/systems/register")
def register(payload: dict):
    system = load_system(payload)
    compiled = compile_system(system)
    return {"system_id": compiled.system_hash, "system_hash": compiled.system_hash}


@app.post("/v1/analysis/paraxial")
def paraxial(payload: dict):
    compiled = _compiled_from_payload(payload)
    return _jsonable(analyze_paraxial(compiled, payload.get("configuration")))


@app.post("/v1/trace/forward")
def forward(payload: dict):
    compiled = _compiled_from_payload(payload)
    trace = trace_forward(
        compiled,
        payload.get("fields", [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]),
        payload.get("ray_sampling", {}),
        payload.get("wavelengths_nm"),
        {**payload.get("options", {}), "configuration": payload.get("configuration", {})},
    )
    return {
        "status": trace.status.tolist(),
        "sensor_y_mm": trace.sensor_y_mm.tolist(),
        "sensor_z_mm": trace.sensor_z_mm.tolist(),
        "paths": trace.paths,
        "metadata": trace.metadata,
    }


@app.post("/v1/trace/reverse")
def reverse(payload: dict):
    compiled = _compiled_from_payload(payload)
    result = trace_reverse(
        compiled,
        payload.get("sensor_points"),
        payload.get("directions"),
        payload.get("wavelengths_nm"),
        {**payload.get("options", {}), "configuration": payload.get("configuration", {})},
    )
    return {
        "status": result.status.tolist(),
        "object_theta_y_deg": result.object_theta_y_deg.tolist(),
        "object_theta_z_deg": result.object_theta_z_deg.tolist(),
        "directions": result.directions.tolist(),
        "metadata": result.metadata,
    }


@app.post("/v1/analysis/spot")
def spot(payload: dict):
    _, trace, evaluation_plane = _trace_for_analysis(payload)
    data = _analysis_response(analyze_spot(trace), evaluation_plane)
    points = [
        {
            "field_id": trace.field_ids[idx],
            "wavelength_nm": float(trace.wavelengths_nm[idx]),
            "sensor_y_mm": None if not trace.sensor_y_mm[idx] == trace.sensor_y_mm[idx] else float(trace.sensor_y_mm[idx]),
            "sensor_z_mm": None if not trace.sensor_z_mm[idx] == trace.sensor_z_mm[idx] else float(trace.sensor_z_mm[idx]),
            "status": str(trace.status[idx]),
        }
        for idx in range(trace.status.size)
    ]
    return _attach_json_artifact(data, "spot", "spot_points", points)


@app.post("/v1/analysis/ray-fan")
def ray_fan(payload: dict):
    compiled, fields, sampling, wavelengths, options, evaluation_plane = _analysis_context(payload)
    result = analyze_ray_fan(
        compiled,
        fields,
        sampling or {"samples_per_field": 21, "pupil_distribution": "fan_y"},
        wavelengths,
        options,
    )
    data = _analysis_response(result, evaluation_plane)
    return _attach_json_artifact(data, "ray_fan", "ray_fan_points", data.get("points", []))


@app.post("/v1/analysis/longitudinal-aberration")
def longitudinal_aberration(payload: dict):
    compiled, fields, sampling, wavelengths, options, evaluation_plane = _analysis_context(payload)
    result = analyze_longitudinal_aberration(
        compiled,
        fields,
        sampling or {"samples_per_field": 21, "pupil_distribution": "fan_y"},
        wavelengths,
        options,
    )
    data = _analysis_response(result, evaluation_plane)
    return _attach_json_artifact(data, "longitudinal", "longitudinal_points", data.get("points", []))


@app.post("/v1/analysis/chromatic-aberration")
def chromatic(payload: dict):
    compiled = _compiled_from_payload(payload)
    result = _jsonable(
        analyze_chromatic_aberration(
            compiled,
            payload.get("wavelengths_nm"),
            payload.get("fields"),
        )
    )
    if "image_plane_policy" in payload:
        resolution = resolve_image_plane_policy(
            compiled,
            payload.get("fields", [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]),
            payload.get("ray_sampling", {}),
            payload.get("wavelengths_nm"),
            {**payload.get("options", {}), "configuration": payload.get("configuration", {})},
            payload.get("image_plane_policy"),
        )
        result = _analysis_response(result, resolution.metadata)
    return result


@app.post("/v1/analysis/distortion")
def distortion(payload: dict):
    compiled, fields, _, wavelengths, options, evaluation_plane = _analysis_context(payload)
    result = analyze_distortion(
        compiled,
        fields,
        wavelengths,
        options,
    )
    return _analysis_response(result, evaluation_plane)


@app.post("/v1/analysis/field-curvature")
def field_curvature(payload: dict):
    compiled = _compiled_from_payload(payload)
    return _jsonable(analyze_field_curvature(compiled, payload.get("fields", []), payload.get("configuration")))


@app.post("/v1/analysis/ms-image-surface")
def ms_image_surface(payload: dict):
    compiled = _compiled_from_payload(payload)
    return _jsonable(analyze_ms_image_surface(compiled, payload.get("fields", []), payload.get("configuration")))


def _analysis_context(payload: dict):
    compiled = _compiled_from_payload(payload)
    fields = payload.get("fields", [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}])
    sampling = payload.get("ray_sampling", {})
    wavelengths = payload.get("wavelengths_nm")
    options = {**payload.get("options", {}), "configuration": payload.get("configuration", {})}
    evaluation_plane = None
    if "image_plane_policy" in payload:
        resolution = resolve_image_plane_policy(compiled, fields, sampling, wavelengths, options, payload.get("image_plane_policy"))
        compiled = resolution.compiled
        options = {**options, "configuration": resolution.configuration}
        evaluation_plane = resolution.metadata
    return compiled, fields, sampling, wavelengths, options, evaluation_plane


def _trace_for_analysis(payload: dict):
    compiled, fields, sampling, wavelengths, options, evaluation_plane = _analysis_context(payload)
    trace = trace_forward(
        compiled,
        fields,
        sampling,
        wavelengths,
        options,
    )
    return compiled, trace, evaluation_plane


@app.post("/v1/analysis/psf")
def psf(payload: dict):
    _, trace, evaluation_plane = _trace_for_analysis(payload)
    data = _analysis_response(
        analyze_geometric_psf(
            trace,
            grid_size=int(payload.get("grid_size", 32)),
            extent_mm=payload.get("extent_mm"),
            encircled_radii_mm=payload.get("encircled_radii_mm"),
        ),
        evaluation_plane,
    )
    return _attach_json_artifact(data, "psf", "psf_array", data.get("grid", []))


@app.post("/v1/analysis/mtf")
def mtf(payload: dict):
    _, trace, evaluation_plane = _trace_for_analysis(payload)
    return _analysis_response(analyze_geometric_mtf(trace, payload.get("frequencies_lp_per_mm", [0.0, 10.0, 20.0])), evaluation_plane)


@app.post("/v1/analysis/relative-illumination")
def relative_illumination(payload: dict):
    compiled = _compiled_from_payload(payload)
    fields = payload.get("fields", [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}])
    sampling = payload.get("ray_sampling", {})
    wavelengths = payload.get("wavelengths_nm")
    options = {**payload.get("options", {}), "configuration": payload.get("configuration", {})}
    evaluation_plane = None
    if "image_plane_policy" in payload:
        resolution = resolve_image_plane_policy(compiled, fields, sampling, wavelengths, options, payload.get("image_plane_policy"))
        compiled = resolution.compiled
        options = {**options, "configuration": resolution.configuration}
        evaluation_plane = resolution.metadata
    return _analysis_response(
        analyze_relative_illumination(
            compiled,
            fields,
            sampling,
            wavelengths,
            options,
        ),
        evaluation_plane,
    )


@app.post("/v1/analysis/white-psf")
def white_psf(payload: dict):
    compiled = _compiled_from_payload(payload)
    fields = payload.get("fields", [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}])
    sampling = payload.get("ray_sampling", {})
    options = {**payload.get("options", {}), "configuration": payload.get("configuration", {})}
    evaluation_plane = None
    if "image_plane_policy" in payload:
        resolution = resolve_image_plane_policy(compiled, fields, sampling, list(payload.get("wavelength_weights", {587.56: 1.0}).keys()), options, payload.get("image_plane_policy"))
        compiled = resolution.compiled
        options = {**options, "configuration": resolution.configuration}
        evaluation_plane = resolution.metadata
    return _analysis_response(
        analyze_white_psf(
            compiled,
            fields,
            sampling,
            {float(k): float(v) for k, v in payload.get("wavelength_weights", {587.56: 1.0}).items()},
            options,
        ),
        evaluation_plane,
    )


@app.post("/v1/analysis/white-mtf")
def white_mtf(payload: dict):
    compiled = _compiled_from_payload(payload)
    fields = payload.get("fields", [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}])
    sampling = payload.get("ray_sampling", {})
    options = {**payload.get("options", {}), "configuration": payload.get("configuration", {})}
    evaluation_plane = None
    if "image_plane_policy" in payload:
        resolution = resolve_image_plane_policy(compiled, fields, sampling, list(payload.get("wavelength_weights", {587.56: 1.0}).keys()), options, payload.get("image_plane_policy"))
        compiled = resolution.compiled
        options = {**options, "configuration": resolution.configuration}
        evaluation_plane = resolution.metadata
    return _analysis_response(
        analyze_white_mtf(
            compiled,
            fields,
            sampling,
            {float(k): float(v) for k, v in payload.get("wavelength_weights", {587.56: 1.0}).items()},
            payload.get("frequencies_lp_per_mm", [0.0, 10.0, 20.0]),
            options,
        ),
        evaluation_plane,
    )


@app.post("/v1/optics/evaluate")
def optics_evaluate(payload: dict):
    system = _compiled_from_payload(payload).system if (payload.get("system_id") or payload.get("system_hash")) else load_system(payload)
    return _jsonable(
        evaluate_system(
            system,
            payload.get("evaluation"),
            configuration=payload.get("configuration"),
            variables=payload.get("variables"),
            ray_sampling=payload.get("ray_sampling"),
        )
    )


@app.post("/v1/optics/evaluate-batch")
def optics_evaluate_batch(payload: dict):
    system = load_system(payload.get("base_system", payload))
    return _jsonable(
        evaluate_batch(
            system,
            payload.get("candidates", []),
            payload.get("evaluation"),
            configuration=payload.get("configuration"),
            ray_sampling=payload.get("ray_sampling"),
            parallel_workers=int(payload.get("parallel_workers", 1)),
        )
    )


@app.post("/v1/analysis/visual-instrument")
def visual_instrument(payload: dict):
    compiled = _compiled_from_payload(payload)
    return _jsonable(
        analyze_afocal(
            compiled,
            (payload.get("fields") or [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}])[0],
            payload.get("ray_sampling"),
            payload.get("configuration"),
        )
    )


@app.post("/v1/analysis/exit-pupil")
def exit_pupil(payload: dict):
    compiled = _compiled_from_payload(payload)
    return _jsonable(analyze_exit_pupil(compiled))


@app.post("/v1/analysis/eye-box")
def eye_box(payload: dict):
    compiled = _compiled_from_payload(payload)
    offsets = [tuple(item) for item in payload.get("offsets_yz_mm", [[0.0, 0.0]])]
    return _jsonable(analyze_eye_box(compiled, offsets, (payload.get("fields") or [None])[0], payload.get("ray_sampling")))


@app.post("/v1/analysis/angular-mtf")
def angular_mtf(payload: dict):
    compiled = _compiled_from_payload(payload)
    trace = trace_forward(
        compiled,
        payload.get("fields", [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]),
        payload.get("ray_sampling", {}),
        payload.get("wavelengths_nm"),
        {**payload.get("options", {}), "configuration": payload.get("configuration", {})},
    )
    return _jsonable(analyze_angular_mtf(trace, payload.get("frequencies_cycles_per_degree", [0.0, 10.0])))


@app.post("/v1/analysis/binocular-alignment")
def binocular_alignment(payload: dict):
    left = compile_system(load_system(payload["left_system"]))
    right = compile_system(load_system(payload["right_system"]))
    field = (payload.get("fields") or [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}])[0]
    return _jsonable(analyze_binocular_alignment(analyze_afocal(left, field), analyze_afocal(right, field, configuration=payload.get("right_configuration"))))


@app.post("/v1/analysis/telescope")
def telescope(payload: dict):
    compiled = _compiled_from_payload(payload)
    return _jsonable(analyze_telescope(compiled, payload.get("true_field_deg")))


@app.post("/v1/solve/best-focus")
def best_focus(payload: dict):
    compiled = _compiled_from_payload(payload)
    fields = payload.get("fields", [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}])
    policy = dict(payload.get("image_plane_policy") or {})
    for key in ("mode", "criteria", "search", "apply_to", "offset_mm", "frequency_lpmm"):
        if key in payload and key not in policy:
            policy[key] = payload[key]
    policy.setdefault("mode", "best_focus_rms")
    policy["apply_to"] = "report_only"
    resolution = resolve_image_plane_policy(
        compiled,
        fields,
        payload.get("ray_sampling", {}),
        payload.get("wavelengths_nm"),
        {**payload.get("options", {}), "configuration": payload.get("configuration", {})},
        policy,
    )
    response = {"evaluation_plane": resolution.metadata}
    if resolution.focus_curve:
        response["focus_curve"] = resolution.focus_curve
        response = _attach_json_artifact(response, "focus", "focus_curve", resolution.focus_curve)
    return response


@app.post("/v1/materials/refractive-index")
def material_refractive_index(payload: dict):
    system = load_system(payload) if ("optical_system" in payload or "surfaces" in payload) else None
    materials = system.materials if system is not None else [Material.model_validate(payload.get("material", payload))]
    material_id = payload.get("material_id") or payload.get("id") or (materials[0].id if materials else "AIR")
    material = next((item for item in materials if item.id == material_id), None)
    if material is None:
        raise HTTPException(
            status_code=404,
            detail=_error_detail(
                "material_not_found",
                f"Unknown material {material_id!r}.",
                params={"material_id": material_id},
            ),
        )
    wavelengths = payload.get("wavelengths_nm") or [payload.get("wavelength_nm", 587.56)]
    return {
        "material_id": material.id,
        "samples": [
            {"wavelength_nm": float(wavelength), "n": float(material.refractive_index(float(wavelength)))}
            for wavelength in wavelengths
        ],
    }


@app.post("/v1/education/preview")
def preview(payload: dict):
    ray_sampling = payload.get("ray_sampling", {})
    ray_sampling.setdefault("ray_aiming", {"mode": "paraxial"})
    return forward({**payload, "ray_sampling": ray_sampling, "options": {**payload.get("options", {}), "store_path": True}})
