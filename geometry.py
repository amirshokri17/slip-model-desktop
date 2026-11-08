"""Geometrical quantities for the laboratory sand prism.

Units: metres for lengths; square metres for exposed rainfall surface;
cubic metres for soil volume.

The upper and lower trapezoid bases run along the slope. `soil_height_m`
is their perpendicular separation (normal to the inclined platform).
The existing infinite-slope SLIP equilibrium is NOT modified by this module.
"""

from math import isfinite


def calculate_geometry(shape, slope_length_m, width_m, soil_height_m,
                       upper_base_m=None, lower_base_m=None):
    """Return soil volume and common exposed slope/rainfall area.

    Rectangle: V = L * W * H; area = L * W.
    Trapezoid side profile: V = ((Lu + Ll)/2) * W * H;
                            exposed area = Lu * W.

    `slope_length_m` remains the characteristic drainage length L for KT=K/L.
    In trapezoid mode it does not enter the geometric volume or area.
    """
    lengths = (slope_length_m, width_m, soil_height_m)
    if not all(isfinite(x) and x > 0 for x in lengths):
        raise ValueError("Slope length, soil width and thickness must be positive finite values.")

    if shape == "Rectangular":
        area = slope_length_m * width_m
        volume = area * soil_height_m
        cross_section = slope_length_m * soil_height_m
    elif shape == "Trapezoidal":
        if (upper_base_m is None or lower_base_m is None or
                not isfinite(upper_base_m) or not isfinite(lower_base_m) or
                upper_base_m <= 0 or lower_base_m <= 0):
            raise ValueError("Trapezoidal upper and lower base lengths must be positive.")
        cross_section = 0.5 * (upper_base_m + lower_base_m) * soil_height_m
        volume = cross_section * width_m
        area = upper_base_m * width_m
    else:
        raise ValueError("Unknown soil shape; select Rectangular or Trapezoidal.")

    if not all(isfinite(x) and x > 0 for x in (volume, area, cross_section)):
        raise ValueError("Calculated geometry is invalid or exceeds numerical limits.")

    return {
        "soil_volume_m3": volume,
        "rainfall_area_m2": area,
        "side_section_m2": cross_section,
        "shape": shape,
    }
