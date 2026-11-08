"""Regression tests for the Desktop v0.7 workflow and exports."""

import csv
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from failure import first_failure, parse_values
from main import SLIPModel
from sensitivity import SensitivityDialog


class FailureTests(unittest.TestCase):
    def test_first_crossing_after_recovery(self):
        rows = [{"time_s": t, "FS": fs}
                for t, fs in [(0, 2), (60, .5), (120, 2), (180, .5)]]
        self.assertEqual(first_failure(rows), (rows[1], 40))
        self.assertEqual(first_failure(rows[1:]), (rows[1], None))
        self.assertEqual(first_failure(rows[:1]), (None, None))
        rows[1]["FS"] = 1
        self.assertEqual(first_failure(rows), (rows[1], 60))

    def test_value_list(self):
        self.assertEqual(parse_values("30,  0.35\n1.5e-5"), [30, .35, 1.5e-5])
        for invalid in ("", "nan", "inf", "30, bad"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_values(invalid)


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.model = SLIPModel()
        self.addCleanup(self.model.deleteLater)
        self.model.show()
        self.app.processEvents()

    def test_default_and_failure_marker(self):
        m = self.model
        self.assertEqual(m.tabs.count(), 2)
        self.assertEqual(m.table.horizontalHeaderItem(3).text(), "m(t)")
        self.assertAlmostEqual(m.latest_results[0]["FS"], 5.925859189117114)
        self.assertAlmostEqual(m.latest_results[-1]["FS"], 1.6417795775649306)
        self.assertEqual(len(m.fs_chart.chart().series()), 2)
        m.fields["intensity"].setText("165.0375")
        m.run_model()
        sample, crossing = first_failure(m.latest_results)
        self.assertEqual(sample["time_s"] / 60, 20)
        self.assertAlmostEqual(crossing / 60, 19.49, places=2)
        self.assertEqual(len(m.fs_chart.chart().series()), 3)
        m.fields["intensity"].setText("bad")
        m.run_model()
        self.assertFalse(m.export_png_button.isEnabled())
        self.assertEqual(m.table.rowCount(), 0)

    def test_sweep_isolated_and_exports(self):
        m = self.model
        base = m.latest_results
        dialog = SensitivityDialog(m)
        dialog.show()
        dialog.parameter.setCurrentIndex(dialog.parameter.findData("intensity"))
        dialog.values.setPlainText("57.5, 165.0375\n-1")
        dialog.run_sweep()
        self.app.processEvents()
        self.assertEqual(dialog.table.rowCount(), 3)
        self.assertEqual(dialog.table.item(0, 5).text(), "No sampled failure")
        self.assertEqual(float(dialog.table.item(1, 3).text()), 20)
        self.assertAlmostEqual(float(dialog.table.item(1, 4).text()), 19.49, places=2)
        self.assertIn("negative", dialog.table.item(2, 5).text())
        self.assertEqual(len(dialog.plot.chart().series()), 4)
        self.assertIs(m.latest_results, base)
        self.assertEqual(m.fields["intensity"].text(), "57.5")
        self.assertEqual(m.active_rain_label.text(), "57.50000 mm/h")

        with TemporaryDirectory(dir=Path.cwd()) as folder:
            for name, export in (("sweep", dialog.export_button.click),
                                 ("primary", m.export_png_button.click)):
                path = Path(folder) / name
                with patch("fs_chart.QFileDialog.getSaveFileName",
                           return_value=(str(path), "")), \
                     patch("fs_chart.QMessageBox.critical", side_effect=AssertionError("PNG save failed")):
                    export()
                image = QImage(str(path.with_suffix(".png")))
                self.assertFalse(image.isNull())
                self.assertGreater(image.width(), 300)
                self.assertGreater(image.height(), 200)

            path = Path(folder) / "results.csv"
            with patch("main.QFileDialog.getSaveFileName", return_value=(str(path), "")), \
                 patch("main.QMessageBox.information"):
                m.export_button.click()
            with path.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.reader(file))
            self.assertEqual(len(rows), 10)
            self.assertEqual(len(rows[0]), 9)
            self.assertEqual(rows[0][3], "m(t)")
            self.assertAlmostEqual(float(rows[-1][-1]), base[-1]["FS"])

        dialog.values.setPlainText("30")
        self.assertFalse(dialog.export_button.isEnabled())
        dialog.close()

    def test_geometry_rain_and_drainage_modes(self):
        m = self.model
        m.geometry_mode.setCurrentText("Trapezoidal")
        m.fields["H"].setText("0.15")
        m.fields["width"].setText("0.8")
        m.rain_mode.setCurrentText("Sprinkler calculated")
        self.assertEqual(m.active_rain_label.text(), "165.03750 mm/h")
        self.assertEqual(m.geometry_volume_label.text(), "0.1812 m³")
        _, changed = m.simulate({"upper_base": 2.4})
        self.assertAlmostEqual(changed[-1]["rain_cumulative_mm"],
                               m.latest_results[-1]["rain_cumulative_mm"] / 2)
        m.kt_mode.setCurrentText("Manual KT")
        soil, _ = m.simulate({"KT": 0.001})
        self.assertEqual(soil.KT, 0.001)
        file = Path(__file__).with_name("reference_rainfall.csv")
        with patch("main.QFileDialog.getOpenFileName", return_value=(str(file), "")):
            m.import_csv()
        self.assertEqual(m.rain_mode.currentText(), "Imported CSV")
        dialog = SensitivityDialog(m)
        self.assertEqual(dialog.parameter.findData("intensity"), -1)
        self.assertEqual(dialog.parameter.findData("pressure"), -1)
        self.assertEqual(dialog.parameter.findData("K"), -1)
        self.assertGreaterEqual(dialog.parameter.findData("KT"), 0)
        _, changed = m.simulate({"phi": 31})
        self.assertEqual(changed[-1]["rain_cumulative_mm"],
                         m.latest_results[-1]["rain_cumulative_mm"])
        self.assertNotEqual(changed[-1]["FS"], m.latest_results[-1]["FS"])
