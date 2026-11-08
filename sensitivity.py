"""Modal one-parameter sweep of the current main-window inputs."""

from PySide6.QtCharts import QChart, QChartView
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from failure import first_failure, parse_values
from fs_chart import draw_fs_chart, export_graph_png


class SensitivityDialog(QDialog):
    def __init__(self, model):
        super().__init__(model)
        self.model = model
        self.setWindowTitle("SLIP Model | Sensitivity Analysis")
        self.resize(900, 720)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Vary one input per run. Other inputs and modes are taken from the main window."
        ))
        form = QFormLayout()
        self.parameter = QComboBox()
        for key, field in model.fields.items():
            if field.isEnabled() and not field.isHidden():
                self.parameter.addItem(model.field_labels[key], key)
        form.addRow("Parameter", self.parameter)
        self.values = QPlainTextEdit()
        self.values.setPlaceholderText("Enter values separated by commas, spaces, or newlines. Use a decimal point.")
        self.values.setMaximumHeight(76)
        form.addRow("Values", self.values)
        layout.addLayout(form)

        actions = QHBoxLayout()
        run = QPushButton("Run Sensitivity Analysis")
        run.clicked.connect(self.run_sweep)
        actions.addWidget(run)
        self.export_button = QPushButton("Export Graph as Picture (PNG)")
        self.export_button.clicked.connect(
            lambda: export_graph_png(self, self.plot, "SLIP_sensitivity.png")
        )
        actions.addWidget(self.export_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.plot = QChartView()
        self.plot.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.plot.setMinimumHeight(260)
        layout.addWidget(self.plot, 3)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Value", "Initial FS", "Minimum FS", "First sampled (min)",
            "Interpolated (min)", "Status",
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 2)
        note = QLabel(
            "Failure criterion: FS ≤ 1. Dotted vertical markers show linear estimates "
            "between samples. A first sample already at or below 1 has no preceding bracket."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.export_button.setEnabled(False)
        self.parameter.currentIndexChanged.connect(self.clear_results)
        self.values.textChanged.connect(self.clear_results)

    def clear_results(self):
        self.message.clear()
        self.table.setRowCount(0)
        if self.export_button.isEnabled():
            previous = self.plot.chart()
            self.plot.setChart(QChart())
            previous.deleteLater()
        self.export_button.setEnabled(False)

    def run_sweep(self):
        self.clear_results()
        try:
            values = parse_values(self.values.toPlainText())
        except ValueError as error:
            self.message.setText(str(error))
            return

        key = self.parameter.currentData()
        label = self.parameter.currentText()
        curves = []
        self.table.setRowCount(len(values))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for index, value in enumerate(values):
                value_text = str(value)
                try:
                    _, results = self.model.simulate({key: value})
                except (ValueError, ArithmeticError) as error:
                    cells = (value_text, "—", "—", "—", "—", str(error))
                else:
                    sample, crossing = first_failure(results)
                    status = "No sampled failure"
                    if sample is not None:
                        status = "First sample ≤ 1" if crossing is None else "Threshold reached"
                    if any(row["saturation_limit_exceeded"] for row in results):
                        status += " | m exceeded its physical limit"
                    cells = (
                        value_text, f"{results[0]['FS']:.4f}",
                        f"{min(row['FS'] for row in results):.4f}",
                        "—" if sample is None else f"{sample['time_s'] / 60:.6g}",
                        "—" if crossing is None else f"{crossing / 60:.6g}",
                        status,
                    )
                    curves.append((value_text, results))
                for column, text in enumerate(cells):
                    self.table.setItem(index, column, QTableWidgetItem(text))
            if curves:
                draw_fs_chart(self.plot, curves, f"Factor of Safety vs Time | {label}",
                              show_legend=True)
        finally:
            QApplication.restoreOverrideCursor()

        self.export_button.setEnabled(bool(curves))
        self.message.setText(f"Valid scenarios: {len(curves)} of {len(values)}")
