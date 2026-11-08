"""SLIP Model Desktop v0.7."""

import sys
import csv
from math import ceil, floor, isfinite
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtCharts import QChart, QChartView
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QPushButton, QLineEdit, QComboBox, QGroupBox,
    QFormLayout, QVBoxLayout, QHBoxLayout,
    QScrollArea, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
)

from slip_engine import SoilParameters, calculate_slip
from geometry import calculate_geometry
from failure import first_failure
from fs_chart import draw_fs_chart, export_graph_png
from sensitivity import SensitivityDialog


def write_results_csv(path, results):
    """Export current nine result fields with higher precision than the UI table."""
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "Time (min)", "Rain since previous time (mm)",
            "Cumulative rain (mm)", "m(t)", "N' (kPa)",
            "C' (kPa)", "W' (kPa)", "F' (kPa)", "FS",
        ])
        for r in results:
            writer.writerow([
                f"{r['time_s'] / 60:.12g}",
                f"{r['rain_interval_mm']:.12g}",
                f"{r['rain_cumulative_mm']:.12g}",
                f"{r['m']:.12g}",
                f"{r['N']:.12g}",
                f"{r['C']:.12g}",
                f"{r['W']:.12g}",
                f"{r['F']:.12g}",
                f"{r['FS']:.12g}",
            ])


class SLIPModel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SLIP Model | Desktop v0.7")
        self.resize(1400, 900)
        self.setMinimumSize(1050, 680)

        self.fields = {}
        self.field_labels = {}
        analysis_menu = self.menuBar().addMenu("&Analysis")
        analysis_menu.addAction("Sensitivity Analysis…", self.open_sensitivity)
        self.imported_events = []
        self.imported_path = None
        self.latest_results = []

        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(20)

        # LEFT — EXISTING INPUT STRUCTURE
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(420)

        panel = QWidget()
        left = QVBoxLayout(panel)
        left.setSpacing(12)

        title = QLabel("SLIP MODEL")
        title.setObjectName("title")
        left.addWidget(title)
        left.addWidget(QLabel("Rainfall-induced shallow landslide analysis"))
        left.addWidget(QLabel("Montrasio & Valentino (2008)"))

        # GEOMETRY — add shape selection without changing SLIP equations.
        geometry_group = QGroupBox("Geometry")
        geometry_form = QFormLayout(geometry_group)
        self.geometry_form = geometry_form
        geometry_form.setSpacing(10)
        self.geometry_mode = QComboBox()
        self.geometry_mode.addItems(["Rectangular", "Trapezoidal"])
        geometry_form.addRow("Soil profile", self.geometry_mode)

        # H is the reference soil thickness used by SLIP, and is assumed
        # to be the perpendicular height in the volume formula.
        self.add_field(geometry_form, "H", "Soil thickness H (m, normal)", "0.30")
        self.add_field(geometry_form, "beta", "Platform slope angle (degrees)", "35")
        self.add_field(geometry_form, "L", "Slope / drainage length L (m)", "20")
        self.add_field(geometry_form, "width", "Soil width W (m)", "20")
        self.add_field(geometry_form, "upper_base", "Upper base length Lu (m)", "1.20")
        self.add_field(geometry_form, "lower_base", "Lower base length Ll (m)", "1.82")
        self.geometry_area_label = QLabel("-")
        self.geometry_volume_label = QLabel("-")
        geometry_form.addRow("Exposed / rainfall area", self.geometry_area_label)
        geometry_form.addRow("Calculated soil volume", self.geometry_volume_label)
        self.geometry_note = QLabel(
            "Area is the exposed slope surface: L × W (rectangle) or Lu × W "
            "(trapezoid). H is used as the representative SLIP thickness."
        )
        self.geometry_note.setWordWrap(True)
        geometry_form.addRow(self.geometry_note)
        left.addWidget(geometry_group)
        self.add_group(left, "Soil properties", [
            ("n", "Porosity", "0.50"),
            ("Gs", "Specific gravity", "2.65"),
            ("phi", "Friction angle (degrees)", "30"),
            ("c", "Effective cohesion (kPa)", "0"),
            ("theta", "Volumetric water content", "0.15"),
            ("gamma_w", "Water unit weight (kN/m³)", "9.81"),
        ])
        self.add_group(left, "SLIP coefficients", [
            ("A", "Apparent cohesion A (kPa)", "40"),
            ("lam", "Lambda", "0.4"),
            ("alpha", "Alpha", "3.4"),
        ])

        drainage = QGroupBox("Drainage")
        drainage_form = QFormLayout(drainage)
        self.kt_mode = QComboBox()
        self.kt_mode.addItems(["Derived K/L", "Manual KT"])
        drainage_form.addRow("Drainage method", self.kt_mode)
        self.add_field(drainage_form, "K", "Hydraulic conductivity K (m/s)", "1.5e-5")
        self.add_field(drainage_form, "KT", "Manual KT (1/s)", "7.5e-7")
        self.active_kt_label = QLabel("Active KT: -")
        drainage_form.addRow("Calculated coefficient", self.active_kt_label)
        left.addWidget(drainage)

        rain = QGroupBox("Rainfall")
        rain_form = QFormLayout(rain)
        self.rain_mode = QComboBox()
        self.rain_mode.addItems([
            "Direct intensity", "Sprinkler calculated", "Imported CSV"
        ])
        rain_form.addRow("Rainfall source", self.rain_mode)
        self.add_field(rain_form, "intensity", "Direct intensity (mm/h)", "57.5")
        self.add_field(rain_form, "rain_duration", "Rainfall duration (min)", "40")
        self.add_field(rain_form, "rain_step", "Rainfall increment (min)", "2")
        self.add_field(rain_form, "sprinklers", "Active sprinklers", "6")
        self.add_field(rain_form, "pressure", "Sprinkler pressure (bar)", "2")

        self.import_button = QPushButton("Import rainfall CSV")
        self.import_button.clicked.connect(self.import_csv)
        rain_form.addRow("Measured rainfall", self.import_button)
        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        rain_form.addRow("Selected file", self.file_label)
        self.active_rain_label = QLabel("Active intensity: -")
        self.active_rain_label.setWordWrap(True)
        rain_form.addRow("Rainfall calculation", self.active_rain_label)
        left.addWidget(rain)

        self.add_group(left, "Simulation", [
            ("sim_duration", "Simulation duration (min)", "40"),
            ("eval_step", "FS evaluation step (min)", "5"),
        ])
        run = QPushButton("Run SLIP Analysis")
        run.clicked.connect(self.run_model)
        run.setMinimumHeight(44)
        left.addWidget(run)
        left.addStretch()
        scroll.setWidget(panel)
        main.addWidget(scroll, 4)

        # RIGHT — EXISTING RESULT STRUCTURE
        result_panel = QWidget()
        right = QVBoxLayout(result_panel)
        right.setSpacing(12)
        heading = QLabel("Stability Analysis")
        heading.setObjectName("title")
        right.addWidget(heading)

        self.summary = QLabel("No calculation performed")
        self.summary.setObjectName("summary")
        right.addWidget(self.summary)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        right.addWidget(self.status)
        self.details = QLabel("")
        self.details.setWordWrap(True)
        right.addWidget(self.details)

        # Export data from the most recent successful simulation.
        export_row = QHBoxLayout()

        self.export_button = QPushButton("Export Results to CSV")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_results_csv)
        export_row.addWidget(self.export_button)
        self.export_png_button = QPushButton("Export Graph as Picture (PNG)")
        self.export_png_button.setEnabled(False)
        self.export_png_button.clicked.connect(self.export_primary_graph)
        export_row.addWidget(self.export_png_button)
        export_row.addStretch()
        right.addLayout(export_row)

        self.tabs = QTabWidget()
        plots = QWidget()
        plots_layout = QVBoxLayout(plots)
        plots_layout.setContentsMargins(4, 8, 4, 4)
        self.fs_chart = QChartView()
        self.fs_chart.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.fs_chart.setMinimumHeight(225)
        plots_layout.addWidget(self.fs_chart)
        self.tabs.addTab(plots, "Stability graph")

        # v0.5: show forces and rainfall depth in the existing results tab.
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Time (min)",
            "Rain since previous time (mm)",
            "Cumulative rain (mm)",
            "m(t)",
            "N′ (kPa)",
            "C′ (kPa)",
            "W′ (kPa)",
            "F′ (kPa)",
            "FS",
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.tabs.addTab(self.table, "Numerical results")
        right.addWidget(self.tabs, 1)
        main.addWidget(result_panel, 6)

        self.kt_mode.currentTextChanged.connect(self.update_modes)
        self.rain_mode.currentTextChanged.connect(self.update_modes)
        self.geometry_mode.currentTextChanged.connect(self.update_geometry_mode)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #f7f9fc;
                color: #26384b;
                font-family: "Segoe UI";
                font-size: 13px;
            }
            QLabel#title {
                font-size: 24px;
                font-weight: bold;
                color: #173653;
            }
            QLabel#summary {
                font-size: 16px;
                font-weight: bold;
                color: #173653;
                padding: 8px 0;
            }
            QGroupBox {
                background: white;
                font-weight: bold;
                border: 1px solid #dce4eb;
                border-radius: 8px;
                margin-top: 14px;
                padding: 15px 10px 10px 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #173653;
            }
            QLineEdit, QComboBox {
                background: white;
                border: 1px solid #b8c9d5;
                border-radius: 5px;
                padding: 7px;
                min-height: 22px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #147d84;
            }
            QLineEdit:disabled {
                background: #edf1f5;
                color: #8a99a8;
            }
            QPushButton {
                background: #147d84;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 11px;
            }
            QPushButton:hover { background: #10666c; }
            QPushButton:disabled { background: #9aabb5; }
            QTabWidget::pane {
                border: 1px solid #dce4eb;
                background: white;
            }
            QTabBar::tab { background: #e9eff4; padding: 10px 18px; }
            QTabBar::tab:selected {
                background: white;
                color: #147d84;
                font-weight: bold;
            }
            QTableWidget {
                background: white;
                alternate-background-color: #f1f6fa;
            }
            QHeaderView::section {
                background: #e9eff4;
                color: #173653;
                padding: 8px;
                font-weight: bold;
            }
        """)
        self.update_geometry_mode(recalculate=False)
        self.update_modes()

    def update_geometry_mode(self, *_args, recalculate=True):
        """Show only the required dimensions for the selected soil shape."""
        trapezoidal = self.geometry_mode.currentText() == "Trapezoidal"
        for key in ("upper_base", "lower_base"):
            field = self.fields[key]
            field.setVisible(trapezoidal)
            label = self.geometry_form.labelForField(field)
            if label is not None:
                label.setVisible(trapezoidal)
        if trapezoidal:
            self.geometry_note.setText(
                "Trapezoidal side profile: V = (Lu + Ll)/2 × H × W; "
                "exposed rainfall area = Lu × W. The L input remains the "
                "characteristic drainage length for K/L. H is a representative "
                "SLIP thickness, not a variable-depth solution."
            )
        else:
            self.geometry_note.setText(
                "Rectangular soil: V = L × W × H; exposed rainfall area = L × W. "
                "H is measured normal to the inclined platform."
            )
        if recalculate:
            self.run_model()

    def open_sensitivity(self):
        dialog = SensitivityDialog(self)
        dialog.exec()
        dialog.deleteLater()

    def export_primary_graph(self):
        if self.latest_results:
            self.tabs.setCurrentIndex(0)
            export_graph_png(self, self.fs_chart, "SLIP_FS.png")

    def export_results_csv(self):
        """Write the currently displayed simulation results, without recalculating."""
        if not self.latest_results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export SLIP results", "SLIP_results.csv", "CSV files (*.csv)"
        )
        if not path:
            return  # User cancelled.
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            write_results_csv(path, self.latest_results)
        except OSError as error:
            QMessageBox.critical(self, "CSV export failed", str(error))
            return
        QMessageBox.information(
            self, "Export complete",
            f"Saved {len(self.latest_results)} time steps to:\n{path}"
        )

    def add_field(self, form, key, label, default):
        edit = QLineEdit(default)
        edit.editingFinished.connect(self.run_model)
        self.fields[key] = edit
        self.field_labels[key] = label
        form.addRow(label, edit)

    def add_group(self, parent, title, items):
        group = QGroupBox(title)
        form = QFormLayout(group)
        form.setSpacing(10)
        for key, label, default in items:
            self.add_field(form, key, label, default)
        parent.addWidget(group)

    def number(self, key):
        try:
            value = float(self.fields[key].text().strip())
        except ValueError:
            raise ValueError(f"Invalid numeric value: {key}") from None
        if not isfinite(value):
            raise ValueError(f"Value must be finite: {key}")
        return value

    def update_modes(self):
        direct = self.rain_mode.currentText() == "Direct intensity"
        sprinkler = self.rain_mode.currentText() == "Sprinkler calculated"
        imported = self.rain_mode.currentText() == "Imported CSV"
        derived = self.kt_mode.currentText() == "Derived K/L"

        self.fields["intensity"].setEnabled(direct)
        self.fields["sprinklers"].setEnabled(sprinkler)
        self.fields["pressure"].setEnabled(sprinkler)
        self.fields["rain_duration"].setEnabled(not imported)
        self.fields["rain_step"].setEnabled(not imported)
        self.import_button.setEnabled(imported)
        self.fields["K"].setEnabled(derived)
        self.fields["KT"].setEnabled(not derived)
        self.run_model()

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import rainfall data", "", "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            events = []
            with open(path, "r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                names = [name.strip().lower() for name in (reader.fieldnames or [])]
                if names != ["time_s", "depth_mm"]:
                    raise ValueError("CSV headers must be: time_s,depth_mm")
                columns = reader.fieldnames
                previous_time = -1.0
                for row in reader:
                    t = float(row[columns[0]])
                    h = float(row[columns[1]])
                    if (not isfinite(t) or not isfinite(h)
                            or t < 0 or h < 0 or t < previous_time):
                        raise ValueError("Invalid or unordered rainfall data.")
                    events.append((t, h / 1000))
                    previous_time = t

            if not events:
                raise ValueError("CSV contains no rainfall events.")
            if len(events) > 10000:
                raise ValueError("Maximum 10000 rainfall events.")

            self.imported_events = events
            self.imported_path = path
            self.file_label.setText(f"{Path(path).name} — {len(events)} events")
            self.rain_mode.setCurrentText("Imported CSV")
            self.run_model()
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.status.setText(f"CSV import error: {error}")

    def prepare(self, number):
        keys = [
            "H", "beta", "L", "width", "n", "Gs", "phi", "c",
            "theta", "gamma_w", "A", "lam", "alpha",
            "sim_duration", "eval_step",
        ]
        v = {key: number(key) for key in keys}
        if not (
            v["H"] > 0 and 0 < v["beta"] < 90
            and v["L"] > 0 and v["width"] > 0
            and 0 < v["n"] < 1 and v["Gs"] > 0
            and 0 <= v["phi"] < 90 and v["c"] >= 0
            and 0 <= v["theta"] < v["n"]
            and v["gamma_w"] > 0 and v["A"] >= 0
            and v["lam"] >= 0 and v["alpha"] >= 0
            and v["sim_duration"] >= 0 and v["eval_step"] > 0
        ):
            raise ValueError("Soil, geometry or simulation inputs invalid.")

        shape = self.geometry_mode.currentText()
        geometry = calculate_geometry(
            shape=shape,
            slope_length_m=v["L"],
            width_m=v["width"],
            soil_height_m=v["H"],
            upper_base_m=number("upper_base") if shape == "Trapezoidal" else None,
            lower_base_m=number("lower_base") if shape == "Trapezoidal" else None,
        )
        v["area"] = geometry["rainfall_area_m2"]
        v["soil_volume"] = geometry["soil_volume_m3"]

        if self.kt_mode.currentText() == "Derived K/L":
            k = number("K")
            if k < 0:
                raise ValueError("Hydraulic conductivity must be >= 0.")
            kt = k / v["L"]
        else:
            kt = number("KT")
            if kt < 0:
                raise ValueError("Manual KT must be >= 0.")

        soil = SoilParameters(
            H=v["H"], beta=v["beta"], n=v["n"],
            Gs=v["Gs"], phi=v["phi"], c=v["c"],
            A=v["A"], lam=v["lam"], alpha=v["alpha"],
            theta=v["theta"], KT=kt, gamma_w=v["gamma_w"],
        )
        return v, soil

    def make_rainfall(self, v, number, update_labels):
        mode = self.rain_mode.currentText()
        if mode == "Imported CSV":
            if not self.imported_events:
                raise ValueError("Import a rainfall CSV before running.")
            if update_labels:
                self.active_rain_label.setText(
                    f"{len(self.imported_events)} measured increments"
                )
            return list(self.imported_events)

        duration = number("rain_duration")
        step = number("rain_step")
        if duration < 0 or step <= 0:
            raise ValueError("Invalid rainfall timing.")

        if mode == "Direct intensity":
            intensity = number("intensity")
            if intensity < 0:
                raise ValueError("Rain intensity cannot be negative.")
        else:
            n = number("sprinklers")
            pressure = number("pressure")
            if n < 1 or not n.is_integer():
                raise ValueError("Sprinkler count must be a positive integer.")
            if not 0.5 <= pressure <= 3.0:
                raise ValueError(
                    "Pressure must be within 0.5–3.0 bar "
                    "for the supplied calibration."
                )
            q = -0.0333 * pressure ** 2 + 0.23 * pressure + 0.1133
            intensity = n * q * 60 / v["area"]

        if update_labels:
            self.active_rain_label.setText(f"{intensity:.5f} mm/h")
        count = ceil(duration / step)
        if count > 10000:
            raise ValueError("Too many rainfall increments.")
        events = []
        for i in range(count):
            start = i * step
            end = min((i + 1) * step, duration)
            depth_m = intensity * (end - start) / 60000
            events.append((end * 60, depth_m))
        return events

    @staticmethod
    def add_rainfall_totals(results, rainfall):
        """Aggregate events into evaluation intervals without shifting timestamps."""
        event_index = 0
        cumulative_m = 0.0
        previous_cumulative_m = 0.0
        for result in results:
            current_time = result["time_s"]
            while (event_index < len(rainfall)
                   and rainfall[event_index][0] <= current_time + 1e-8):
                cumulative_m += rainfall[event_index][1]
                event_index += 1
            result["rain_interval_mm"] = (
                cumulative_m - previous_cumulative_m
            ) * 1000
            result["rain_cumulative_mm"] = cumulative_m * 1000
            previous_cumulative_m = cumulative_m

    def simulate(self, overrides=None):
        def number(key):
            if overrides is not None and key in overrides:
                return overrides[key]
            return self.number(key)

        v, soil = self.prepare(number)
        if overrides is None:
            self.geometry_area_label.setText(f"{v['area']:.6g} m²")
            self.geometry_volume_label.setText(f"{v['soil_volume']:.6g} m³")
            self.active_kt_label.setText(f"{soil.KT:.6e} s^-1")
        rainfall = self.make_rainfall(v, number, update_labels=overrides is None)
        count = floor(v["sim_duration"] / v["eval_step"]) + 1
        if (count > 10000 or len(rainfall) > 10000
                or count * max(1, len(rainfall)) > 2000000):
            raise ValueError("Too many calculations. Increase time steps.")

        times = [i * v["eval_step"] for i in range(count)]
        if times[-1] < v["sim_duration"] - 1e-9:
            times.append(v["sim_duration"])
        results = [
            calculate_slip(soil, rainfall, t * 60)
            for t in times
        ]

        # v0.5: rainfall received by each sampled time.
        self.add_rainfall_totals(results, rainfall)

        if not all(isfinite(r["FS"]) for r in results):
            raise ValueError("Nonfinite FS. Check the input magnitudes.")
        return soil, results

    def run_model(self):
        try:
            soil, results = self.simulate()
            initial_fs = results[0]["FS"]
            minimum_fs = min(r["FS"] for r in results)
            failure_record, crossing = first_failure(results)
            self.summary.setText(
                f"Initial FS: {initial_fs:.4f}    |    "
                f"Minimum FS: {minimum_fs:.4f}"
            )

            if failure_record is None:
                self.status.setText(
                    "No sampled FS ≤ 1 within simulation period"
                )
                critical_rain = "Not reached"
            else:
                estimate = ("unavailable (first sample ≤ 1)" if crossing is None
                            else f"{crossing / 60:.2f} min")
                self.status.setText(
                    f"First sampled FS ≤ 1 at {failure_record['time_s'] / 60:.2f} min"
                    f" | Estimated graphical crossing: {estimate}"
                )
                critical_rain = (
                    f"{failure_record['rain_cumulative_mm']:.3f} mm"
                )
            if any(r["saturation_limit_exceeded"] for r in results):
                self.status.setText(
                    self.status.text()
                    + " | WARNING: m exceeded its physical limit"
                )

            total_mm = results[-1]["rain_cumulative_mm"]
            self.details.setText(
                f"Initial Sr: {soil.theta / soil.n:.4f}    |    "
                f"Applied rainfall: {total_mm:.3f} mm    |    "
                f"Rain at first sampled failure: {critical_rain}    |    "
                f"Evaluation points: {len(results)}"
            )

            self.table.setRowCount(len(results))
            for row, r in enumerate(results):
                values = [
                    f"{r['time_s'] / 60:g}",
                    f"{r['rain_interval_mm']:.3f}",
                    f"{r['rain_cumulative_mm']:.3f}",
                    f"{r['m']:.6f}",
                    f"{r['N']:.4f}",
                    f"{r['C']:.4f}",
                    f"{r['W']:.4f}",
                    f"{r['F']:.4f}",
                    f"{r['FS']:.4f}",
                ]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, col, item)

            draw_fs_chart(self.fs_chart, [("FS", results)], "Factor of Safety vs Time")
            self.latest_results = results
            self.export_button.setEnabled(True)
            self.export_png_button.setEnabled(True)

        except (ValueError, ZeroDivisionError, OverflowError) as error:
            self.latest_results = []
            self.export_button.setEnabled(False)
            self.export_png_button.setEnabled(False)
            self.summary.setText("No valid results")
            self.status.setText(f"Input error: {error}")
            self.details.setText("")
            self.table.setRowCount(0)
            previous = self.fs_chart.chart()
            self.fs_chart.setChart(QChart())
            previous.deleteLater()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SLIPModel()
    window.show()
    sys.exit(app.exec())
