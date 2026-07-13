from __future__ import annotations

from .models import OpticalSystem


def gullstrand_visual_composite_demo() -> OpticalSystem:
    """Return the monochromatic relaxed simplified-Gullstrand demo system."""

    return OpticalSystem.model_validate(
        {
            "name": "Gullstrand Visual Composite Demo",
            "system_type": "afocal",
            "visual_evaluation": {
                "mode": "instrument_and_retinal",
                "eye_model": "gullstrand_simplified_relaxed",
                "wavelength_nm": 587.56,
                "accommodation_diopter": 0.0,
                "retina_surface": "plane",
            },
            "wavelengths_nm": {"primary": 587.56, "samples": [587.56]},
            "materials": [
                {"id": "AIR", "type": "constant", "n": 1.0},
                {"id": "CORNEA", "type": "constant", "n": 1.376},
                {"id": "AQUEOUS_VITREOUS", "type": "constant", "n": 1.336},
                {"id": "LENS_EQ", "type": "constant", "n": 1.4085},
            ],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "surface_type": "plane",
                    "aperture": {"shape": "circle", "semi_diameter_mm": 25.0},
                    "semi_diameter_mm": 25.0,
                },
                {
                    "id": "OBJ",
                    "kind": "thin_lens",
                    "surface_type": "plane",
                    "focal_length_mm": 100.0,
                    "thickness_after_mm": 120.0,
                    "semi_diameter_mm": 25.0,
                },
                {
                    "id": "EYEPIECE",
                    "kind": "thin_lens",
                    "surface_type": "plane",
                    "focal_length_mm": 20.0,
                    "thickness_after_mm": 20.0,
                    "semi_diameter_mm": 10.0,
                },
                {
                    "id": "EYE",
                    "kind": "eye_reference",
                    "surface_type": "plane",
                    "eye": {"pupil_diameter_mm": 4.0, "position_mode": "at_exit_pupil"},
                },
                {
                    "id": "CORNEA_FRONT",
                    "kind": "refractive",
                    "radius_mm": 7.70,
                    "thickness_after_mm": 0.50,
                    "material_after": "CORNEA",
                    "semi_diameter_mm": 6.0,
                },
                {
                    "id": "CORNEA_BACK",
                    "kind": "refractive",
                    "radius_mm": 6.80,
                    "thickness_after_mm": 3.10,
                    "material_after": "AQUEOUS_VITREOUS",
                    "semi_diameter_mm": 6.0,
                },
                {
                    "id": "LENS_FRONT",
                    "kind": "refractive",
                    "radius_mm": 10.0,
                    "thickness_after_mm": 3.60,
                    "material_after": "LENS_EQ",
                    "semi_diameter_mm": 5.0,
                },
                {
                    "id": "LENS_BACK",
                    "kind": "refractive",
                    "radius_mm": -6.00,
                    "thickness_after_mm": 17.187,
                    "material_after": "AQUEOUS_VITREOUS",
                    "semi_diameter_mm": 5.0,
                },
                {
                    "id": "RETINA",
                    "kind": "sensor",
                    "surface_type": "plane",
                    "sensor": {"width_mm": 24.0, "height_mm": 24.0},
                },
            ],
            "metadata": {
                "preset_family": "schematic_eye",
                "source": "Wiley-VCH Handbook of Optical Systems, Table 36-8",
                "limitations": ["monochromatic_587_56_nm", "fixed_4_mm_pupil", "unaccommodated", "planar_retina"],
            },
        }
    )
