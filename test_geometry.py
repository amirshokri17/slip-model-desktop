"""Run: python -m unittest -v test_geometry.py (no PySide6 needed)."""
import unittest
from geometry import calculate_geometry
from slip_engine import SoilParameters, calculate_slip


class GeometryRegression(unittest.TestCase):
    def test_original_rectangular_area(self):
        g = calculate_geometry("Rectangular", 20.0, 20.0, 0.30)
        self.assertAlmostEqual(g["rainfall_area_m2"], 400.0)
        self.assertAlmostEqual(g["soil_volume_m3"], 120.0)

    def test_lab_trapezoid(self):
        g = calculate_geometry("Trapezoidal", 1.82, 0.80, 0.15, 1.20, 1.82)
        self.assertAlmostEqual(g["soil_volume_m3"], 0.1812)
        self.assertAlmostEqual(g["rainfall_area_m2"], 0.96)

    def test_invalid_dimensions_rejected(self):
        with self.assertRaises(ValueError):
            calculate_geometry("Rectangular", -20, 20, 0.3)
        with self.assertRaises(ValueError):
            calculate_geometry("Trapezoidal", 1.82, .8, .15, 0, 1.82)

    def test_original_slip_reference_unchanged(self):
        soil = SoilParameters(H=.30, beta=35, n=.5, Gs=2.65,
                              phi=30, c=0, A=40, lam=.4,
                              alpha=3.4, theta=.15, KT=7.5e-7)
        events = [(i * 120, 57.5 / 1000 * (2 / 60)) for i in range(1,21)]
        self.assertAlmostEqual(calculate_slip(soil, events, 0)["FS"], 5.925859189117114)
        self.assertAlmostEqual(calculate_slip(soil, events, 2400)["FS"], 1.6417795775649306)

    def test_sprinkler_intensity_consistent_with_auto_area(self):
        g=calculate_geometry("Trapezoidal",1.82,.8,.15,1.2,1.82)
        q = -0.0333*2**2+0.23*2+0.1133
        intensity = 6*q*60/g["rainfall_area_m2"]
        self.assertAlmostEqual(intensity, 165.0375)

if __name__ == "__main__":
    unittest.main()
