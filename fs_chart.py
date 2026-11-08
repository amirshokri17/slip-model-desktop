"""Shared factor-of-safety chart and PNG export."""

from itertools import cycle
from pathlib import Path

from PySide6.QtCharts import QChart, QLineSeries, QValueAxis
from PySide6.QtCore import QMargins, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QFileDialog, QMessageBox

from failure import first_failure


def draw_fs_chart(view, curves, title, show_legend=False):
    chart = QChart()
    chart.setTitle(title)
    chart.legend().setVisible(show_legend)
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
    chart.setMargins(QMargins(22, 8, 18, 8))

    xmax = max(1, max(rows[-1]["time_s"] / 60 for _, rows in curves))
    ymax = max(1.1, max(row["FS"] for _, rows in curves for row in rows) * 1.1)
    x = QValueAxis()
    x.setTitleText("Time (min)")
    x.setRange(0, xmax)
    x.setTickCount(6)
    y = QValueAxis()
    y.setTitleText("FS")
    y.setRange(0, ymax)
    y.setTickCount(5)
    y.setLabelFormat("%.2f")
    chart.addAxis(x, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(y, Qt.AlignmentFlag.AlignLeft)

    def add_line(name, points, color, width, style, legend=True, point=False):
        series = QLineSeries()
        series.setName(name)
        for t, fs in points:
            series.append(t, fs)
        series.setPointsVisible(point)
        pen = QPen(QColor(color))
        pen.setWidth(width)
        pen.setStyle(style)
        series.setPen(pen)
        chart.addSeries(series)
        series.attachAxis(x)
        series.attachAxis(y)
        if not legend:
            for marker in chart.legend().markers(series):
                marker.setVisible(False)

    solid = Qt.PenStyle.SolidLine
    dash = Qt.PenStyle.DashLine
    add_line("FS = 1", [(0, 1), (xmax, 1)], "#d44e52", 2, dash)
    colors = ("#147d84", "#315bbb", "#7a42a8", "#b86317", "#25793d", "#9a365c")
    styles = (solid, dash, Qt.PenStyle.DashDotLine, Qt.PenStyle.DotLine)
    palette = cycle((color, style) for style in styles for color in colors)
    for (label, rows), (color, style) in zip(curves, palette):
        add_line(label, ((r["time_s"] / 60, r["FS"]) for r in rows),
                 color, 3, style, point=len(rows) == 1)
        _, crossing = first_failure(rows)
        if crossing is not None:
            t = crossing / 60
            marker_color = color if show_legend else "#d38121"
            add_line("", [(t, 0), (t, 1)], marker_color, 2,
                     Qt.PenStyle.DotLine if show_legend else dash, legend=False)

    previous = view.chart()
    view.setChart(chart)
    if previous is not None:
        previous.deleteLater()


def export_graph_png(parent, view, filename):
    path, _ = QFileDialog.getSaveFileName(
        parent, "Export Graph as Picture", filename, "PNG files (*.png)"
    )
    if not path:
        return
    if Path(path).suffix.lower() != ".png":
        path += ".png"
    pixmap = view.grab()
    if not pixmap.save(path, "PNG"):
        QMessageBox.critical(parent, "PNG export failed", f"Could not save to:\n{path}")
