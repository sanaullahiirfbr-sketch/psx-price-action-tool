"""
PySide6 Graphical User Interface Application for PSX Technical Analyzer.
Optimized for low-resource hardware (HP Notebook i5-4210U, 8GB RAM).
"""

import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QListWidget, QProgressBar, QLabel,
    QTextEdit, QSplitter, QComboBox, QGroupBox, QLineEdit, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QPixmap

from config import AppConfig, PerformanceMode
from diagnostics import ResourceMonitor
from storage import StorageManager
from pipeline import ProcessingPipeline


class WorkerThread(QThread):
    """Background worker thread to run CPU-intensive processing sequentially without freezing GUI."""

    progress_signal = Signal(int, int, str, dict)
    finished_signal = Signal(list)

    def __init__(self, pipeline: ProcessingPipeline, file_paths: list):
        super().__init__()
        self.pipeline = pipeline
        self.file_paths = file_paths

    def run(self):
        def on_progress(current, total, stage, metrics):
            self.progress_signal.emit(current, total, stage, metrics)

        results = self.pipeline.process_images(self.file_paths, progress_callback=on_progress)
        self.finished_signal.emit(results)


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("PSX Technical Analyzer (Hardware-Optimized)")
        self.resize(1100, 700)

        # Core Components
        self.config = AppConfig(PerformanceMode.STANDARD)
        self.storage = StorageManager(self.config.db_path)
        self.monitor = ResourceMonitor()
        self.pipeline = ProcessingPipeline(self.config, self.storage, self.monitor)

        self.image_files = []
        self.selected_file = None
        self.worker_thread = None

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Control Bar
        top_bar = QHBoxLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["STANDARD / LIGHTWEIGHT MODE", "HIGH ACCURACY / ADVANCED MODE"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        btn_add_files = QPushButton("Upload TradingView Images")
        btn_add_files.clicked.connect(self._browse_images)

        btn_run = QPushButton("Run Analysis")
        btn_run.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
        btn_run.clicked.connect(self._run_analysis)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet("background-color: #c62828; color: white;")
        self.btn_cancel.clicked.connect(self._cancel_analysis)

        top_bar.addWidget(QLabel("Performance Mode:"))
        top_bar.addWidget(self.mode_combo)
        top_bar.addSpacing(20)
        top_bar.addWidget(btn_add_files)
        top_bar.addWidget(btn_run)
        top_bar.addWidget(self.btn_cancel)
        top_bar.addStretch()

        main_layout.addLayout(top_bar)

        # Progress Section
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.status_label = QLabel("Status: Ready")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)

        main_layout.addLayout(progress_layout)

        # Content Splitter (Left: File List & Thumbnails, Middle: Manual Correction, Right: Reports & Diagnostic Overlay)
        splitter = QSplitter(Qt.Horizontal)

        # Left Panel: Files
        left_group = QGroupBox("Uploaded Images Queue")
        left_layout = QVBoxLayout(left_group)
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self._on_file_selected)

        self.thumb_label = QLabel("Thumbnail Preview")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setFixedSize(220, 180)
        self.thumb_label.setStyleSheet("border: 1px dashed gray;")

        left_layout.addWidget(self.file_list)
        left_layout.addWidget(self.thumb_label, alignment=Qt.AlignCenter)

        # Middle Panel: Data Correction Editor (Section 89)
        mid_group = QGroupBox("Extracted Numerical Data / Manual Correction")
        mid_layout = QFormLayout(mid_group)

        self.input_symbol = QLineEdit()
        self.input_price = QLineEdit()
        self.input_rsi = QLineEdit()
        self.input_status = QLineEdit()
        self.input_status.setReadOnly(True)

        btn_save_corrections = QPushButton("Save Data Corrections")
        btn_save_corrections.clicked.connect(self._save_manual_corrections)

        mid_layout.addRow("Stock Symbol:", self.input_symbol)
        mid_layout.addRow("Last Price:", self.input_price)
        mid_layout.addRow("RSI Value:", self.input_rsi)
        mid_layout.addRow("Extraction Status:", self.input_status)
        mid_layout.addRow(btn_save_corrections)

        # Right Panel: Analysis Report & Resource Diagnostic Overlay
        right_group = QGroupBox("Technical Analysis Report & System Diagnostics")
        right_layout = QVBoxLayout(right_group)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)

        # Section 88: Diagnostic overlay
        self.diag_label = QLabel("Diagnostics: RAM: 0 MB | CPU: 0%")
        self.diag_label.setStyleSheet("background-color: #212121; color: #00e676; padding: 6px; font-family: monospace;")

        right_layout.addWidget(self.report_text)
        right_layout.addWidget(self.diag_label)

        splitter.addWidget(left_group)
        splitter.addWidget(mid_group)
        splitter.addWidget(right_group)
        splitter.setSizes([300, 300, 500])

        main_layout.addWidget(splitter)

    def _on_mode_changed(self, index: int):
        mode = PerformanceMode.STANDARD if index == 0 else PerformanceMode.ADVANCED
        self.config.set_mode(mode)
        self.status_label.setText(f"Status: Mode set to {mode.value}")

    def _browse_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select TradingView Screenshots", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if files:
            for f in files:
                if f not in self.image_files:
                    self.image_files.append(f)
                    self.file_list.addItem(os.path.basename(f))

    def _on_file_selected(self, item):
        idx = self.file_list.row(item)
        if 0 <= idx < len(self.image_files):
            self.selected_file = self.image_files[idx]
            self._load_file_details(self.selected_file)

    def _load_file_details(self, file_path: str):
        record = self.storage.get_record(file_path)
        if not record:
            self.report_text.setText("No analysis record available yet. Click 'Run Analysis'.")
            return

        # Show thumbnail
        thumb_path = record.get("thumbnail_path")
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path)
            self.thumb_label.setPixmap(pixmap.scaled(200, 160, Qt.KeepAspectRatio))

        # Show values in manual correction editor
        ocr_data = record.get("ocr_data", {})
        values = ocr_data.get("values", {})
        self.input_symbol.setText(str(values.get("symbol", "")))
        self.input_price.setText(str(values.get("last_price", "")))
        self.input_rsi.setText(str(values.get("rsi", "")))
        self.input_status.setText(record.get("status", ""))

        # Show report text
        report = record.get("report", {})
        summary = report.get("summary_text", "No summary available.")
        self.report_text.setText(summary)

    def _save_manual_corrections(self):
        if not self.selected_file:
            QMessageBox.warning(self, "Warning", "Select an image from the queue first.")
            return

        record = self.storage.get_record(self.selected_file) or {}
        ocr_data = record.get("ocr_data", {})
        values = ocr_data.get("values", {})

        values["symbol"] = self.input_symbol.text().strip()
        try:
            values["last_price"] = float(self.input_price.text()) if self.input_price.text() else None
        except ValueError:
            values["last_price"] = None

        try:
            values["rsi"] = float(self.input_rsi.text()) if self.input_rsi.text() else None
        except ValueError:
            values["rsi"] = None

        ocr_data["values"] = values
        ocr_data["status"] = "MANUALLY_CORRECTED"

        self.storage.save_analysis_record(
            file_path=self.selected_file,
            status="MANUALLY_CORRECTED",
            ocr_data=ocr_data,
            vision_data=record.get("vision_data", {}),
            patterns=record.get("patterns", []),
            report=record.get("report", {}),
            thumbnail_path=record.get("thumbnail_path")
        )

        QMessageBox.information(self, "Saved", "Manual corrections saved successfully.")
        self._load_file_details(self.selected_file)

    def _run_analysis(self):
        if not self.image_files:
            QMessageBox.warning(self, "Warning", "Upload at least one image to run analysis.")
            return

        self.btn_cancel.setEnabled(True)
        self.status_label.setText("Starting sequential processing...")

        self.worker_thread = WorkerThread(self.pipeline, self.image_files)
        self.worker_thread.progress_signal.connect(self._on_progress_update)
        self.worker_thread.finished_signal.connect(self._on_analysis_finished)
        self.worker_thread.start()

    def _cancel_analysis(self):
        if self.pipeline:
            self.pipeline.cancel()
            self.status_label.setText("Cancellation requested...")

    @Slot(int, int, str, dict)
    def _on_progress_update(self, current: int, total: int, stage: str, metrics: dict):
        percent = int((current / float(total)) * 100)
        self.progress_bar.setValue(percent)

        msg = f"Processing Image {current} of {total} | Stage: {stage}"
        self.status_label.setText(msg)

        # Update Section 88 Diagnostic Monitor Overlay
        ram_mb = metrics.get("process_ram_mb", 0)
        cpu_pct = metrics.get("cpu_percent", 0)
        sys_ram_gb = metrics.get("system_ram_used_gb", 0)
        sys_ram_tot = metrics.get("system_ram_total_gb", 0)

        diag_msg = f"Diagnostics: App RAM: {ram_mb} MB | Sys RAM: {sys_ram_gb}/{sys_ram_tot} GB | CPU: {cpu_pct}%"
        self.diag_label.setText(diag_msg)

    @Slot(list)
    def _on_analysis_finished(self, results: list):
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100)
        self.status_label.setText("Analysis finished!")

        if self.image_files:
            self.selected_file = self.image_files[0]
            self._load_file_details(self.selected_file)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
