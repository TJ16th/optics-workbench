from optics_engine import load_system


WAVELENGTHS = [486.13, 587.56, 656.27]


def glass_materials():
    return [
        {"id": "AIR", "type": "constant", "n": 1.0},
        {
            "id": "N-BK7",
            "type": "sellmeier",
            "B": [1.03961212, 0.231792344, 1.01046945],
            "C": [0.00600069867, 0.0200179144, 103.560653],
        },
        {
            "id": "N-F2",
            "type": "sellmeier",
            "B": [1.34533359, 0.209073176, 0.937357162],
            "C": [0.00997743871, 0.0470450767, 111.886764],
        },
    ]


def achromat_doublet_100mm():
    return load_system(
        {
            "name": "golden_bk7_f2_achromat_doublet_100mm",
            "wavelengths_nm": {"primary": 587.56, "samples": WAVELENGTHS},
            "materials": glass_materials(),
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "thickness_after_mm": 5.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 12.5},
                },
                {
                    "id": "S1",
                    "kind": "refractive",
                    "radius_mm": 49.35032280917523,
                    "material_after": "N-BK7",
                    "thickness_after_mm": 7.5,
                    "semi_diameter_mm": 12.5,
                },
                {
                    "id": "S2",
                    "kind": "refractive",
                    "radius_mm": -37.89173520260854,
                    "material_after": "N-F2",
                    "thickness_after_mm": 3.0,
                    "semi_diameter_mm": 12.5,
                },
                {
                    "id": "S3",
                    "kind": "refractive",
                    "radius_mm": -273.82424779569635,
                    "material_after": "AIR",
                    "thickness_after_mm": 93.33699484632511,
                    "semi_diameter_mm": 12.5,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
        }
    )


def cassegrain_v2_3():
    return load_system(
        {
            "name": "golden_cassegrain_v2_3",
            "surfaces": [
                {"id": "M1", "kind": "mirror", "radius_mm": -2000.0, "thickness_after_mm": -650.0, "semi_diameter_mm": 100.0},
                {"id": "M2", "kind": "mirror", "radius_mm": -1050.0, "thickness_after_mm": 1050.0, "semi_diameter_mm": 40.0},
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 30.0, "height_mm": 30.0}},
            ],
        }
    )
