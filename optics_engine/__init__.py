from .aberrations import (
    DistortionResult,
    LongitudinalAberrationResult,
    RayFanResult,
    analyze_distortion,
    analyze_longitudinal_aberration,
    analyze_ray_fan,
)
from .analysis import SpotResult, analyze_spot
from .chromatic import ChromaticAberrationResult, analyze_chromatic_aberration
from .configuration import RuntimeLayout, runtime_layout, symmetric_fields, validate_configuration
from .field_curvature import FieldCurvatureResult, MSImageSurfaceResult, analyze_field_curvature, analyze_ms_image_surface
from .image_plane import EvaluationPlaneResolution, resolve_image_plane_policy
from .metadata import health_payload, meta_payload
from .models import OpticalSystem, ValidationResult
from .optimization import (
    BatchEvaluateResult,
    EvaluateResult,
    MeritResult,
    apply_variables,
    evaluate_batch,
    evaluate_system,
)
from .paraxial import ParaxialResult, analyze_paraxial
from .psf_mtf import (
    GeometricMTFResult,
    GeometricPSFResult,
    RelativeIlluminationResult,
    WhiteMTFResult,
    WhitePSFResult,
    analyze_geometric_mtf,
    analyze_geometric_psf,
    analyze_relative_illumination,
    analyze_white_mtf,
    analyze_white_psf,
    encircled_energy,
)
from .presets import gullstrand_visual_composite_demo
from .system import CompiledSystem, compile_system, get_cached_system
from .tracing import ReverseTraceResult, TraceResult, trace_forward, trace_reverse
from .validation import validate_system
from .visual import (
    AfocalEvaluationResult,
    AngularMTFResult,
    BinocularAlignmentResult,
    ExitPupilResult,
    EyeBoxResult,
    TelescopeResult,
    VisualCompositeResult,
    afocal_from_trace,
    analyze_afocal,
    analyze_angular_mtf,
    analyze_binocular_alignment,
    analyze_exit_pupil,
    analyze_eye_box,
    analyze_telescope,
    analyze_visual_composite,
    angular_magnification,
)


def load_system(data: dict) -> OpticalSystem:
    """Load an optical system from a plain dict.

    The spec examples wrap the payload under ``optical_system``; direct payloads
    are accepted too for API ergonomics.
    """

    payload = data.get("optical_system", data)
    return OpticalSystem.model_validate(payload)


__all__ = [
    "CompiledSystem",
    "ChromaticAberrationResult",
    "BatchEvaluateResult",
    "AfocalEvaluationResult",
    "AngularMTFResult",
    "BinocularAlignmentResult",
    "EvaluateResult",
    "EvaluationPlaneResolution",
    "ExitPupilResult",
    "EyeBoxResult",
    "DistortionResult",
    "OpticalSystem",
    "FieldCurvatureResult",
    "GeometricMTFResult",
    "GeometricPSFResult",
    "MSImageSurfaceResult",
    "LongitudinalAberrationResult",
    "MeritResult",
    "ParaxialResult",
    "RuntimeLayout",
    "RelativeIlluminationResult",
    "ReverseTraceResult",
    "RayFanResult",
    "SpotResult",
    "TraceResult",
    "TelescopeResult",
    "VisualCompositeResult",
    "ValidationResult",
    "WhiteMTFResult",
    "WhitePSFResult",
    "analyze_paraxial",
    "analyze_afocal",
    "analyze_angular_mtf",
    "analyze_binocular_alignment",
    "analyze_chromatic_aberration",
    "analyze_distortion",
    "analyze_exit_pupil",
    "analyze_eye_box",
    "analyze_field_curvature",
    "analyze_geometric_mtf",
    "analyze_geometric_psf",
    "analyze_ms_image_surface",
    "analyze_longitudinal_aberration",
    "analyze_ray_fan",
    "analyze_spot",
    "analyze_relative_illumination",
    "analyze_white_mtf",
    "analyze_white_psf",
    "analyze_telescope",
    "analyze_visual_composite",
    "afocal_from_trace",
    "angular_magnification",
    "apply_variables",
    "compile_system",
    "evaluate_batch",
    "evaluate_system",
    "get_cached_system",
    "gullstrand_visual_composite_demo",
    "load_system",
    "health_payload",
    "meta_payload",
    "encircled_energy",
    "resolve_image_plane_policy",
    "trace_forward",
    "trace_reverse",
    "runtime_layout",
    "symmetric_fields",
    "validate_configuration",
    "validate_system",
]
