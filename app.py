"""
PSX Price Action and Overtrading Analysis Tool
Foundational Application Module with Memory-Conscious Modular Architecture
Target Hardware: Intel Core i5-4210U | 8 GB RAM | Windows 10 Home (64-bit)
"""

import sys
import os
import sqlite3
import logging
import gc
from typing import List, Dict, Any, Optional
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PSX_Tool")


class ExecutionMode(str, Enum):
    STANDARD = "Standard (Lightweight)"
    ADVANCED = "Advanced (Placeholder)"


class MemoryMonitor:
    """Utility to monitor process memory usage and ensure operation within 2-3 GB limits."""

    @staticmethod
    def get_memory_usage_mb() -> float:
        try:
            import resource
            usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return usage_kb / 1024.0
        except ImportError:
            # Fallback on non-Unix systems or Windows where resource may differ
            try:
                import psutil
                process = psutil.Process(os.getpid())
                return process.memory_info().rss / (1024.0 * 1024.0)
            except Exception:
                return 0.0


class DatabaseManager:
    """Lightweight SQLite database manager for storing PSX trade logs and analysis results."""

    def __init__(self, db_path: str = "psx_analysis.db"):
        self.db_path = db_path
        self._persistent_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(":memory:")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._persistent_conn is not None:
            return self._persistent_conn
        return sqlite3.connect(self.db_path)

    def _close_connection_if_transient(self, conn: sqlite3.Connection) -> None:
        if self._persistent_conn is None:
            conn.close()

    def _init_db(self) -> None:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    price REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    overtrading_score REAL DEFAULT 0.0
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    details TEXT
                );
            """)
            conn.commit()
        finally:
            self._close_connection_if_transient(conn)
        logger.info(f"Database initialized at {self.db_path}")

    def log_trade(self, symbol: str, timestamp: str, price: float, volume: int, action: str, overtrading_score: float = 0.0) -> None:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO trade_logs (symbol, timestamp, price, volume, action, overtrading_score) VALUES (?, ?, ?, ?, ?, ?)",
                (symbol, timestamp, price, volume, action, overtrading_score)
            )
            conn.commit()
        finally:
            self._close_connection_if_transient(conn)

    def get_trade_count(self) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trade_logs")
            return cursor.fetchone()[0]
        finally:
            self._close_connection_if_transient(conn)


class SequentialImageProcessor:
    """
    Sequential image processing pipeline.
    Processes images strictly 1 at a time to keep RAM consumption low on dual-core CPU system.
    """

    def __init__(self, mode: ExecutionMode = ExecutionMode.STANDARD):
        self.mode = mode

    def process_single_image(self, image_path: str) -> Dict[str, Any]:
        """Loads and processes 1 image, then releases resources immediately."""
        logger.info(f"Processing image sequentially in {self.mode.value} mode: {image_path}")

        result = {
            "image_path": image_path,
            "status": "pending",
            "width": 0,
            "height": 0,
            "mean_intensity": 0.0,
            "mode": self.mode.value
        }

        if not os.path.exists(image_path):
            result["status"] = "file_not_found"
            return result

        try:
            # Import image processing libraries lazily inside method if needed
            from PIL import Image
            import numpy as np

            with Image.open(image_path) as img:
                result["width"], result["height"] = img.size
                arr = np.array(img.convert('L'))
                result["mean_intensity"] = float(np.mean(arr))
                result["status"] = "success"

                # Standard mode uses lightweight basic signal detection
                if self.mode == ExecutionMode.ADVANCED:
                    result["details"] = "Advanced mode feature extraction placeholder"
                else:
                    result["details"] = "Standard mode lightweight image analysis complete"

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            result["status"] = f"error: {str(e)}"
        finally:
            # Force garbage collection after single image processing to prevent RAM accumulation
            gc.collect()

        return result

    def process_batch_sequentially(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """Processes a list of image paths strictly one by one."""
        results = []
        for path in image_paths:
            res = self.process_single_image(path)
            results.append(res)
            logger.debug(f"Memory RSS after processing {path}: {MemoryMonitor.get_memory_usage_mb():.2f} MB")
        return results


class PriceActionAnalyzer:
    """Lightweight analytical engine for PSX price action and overtrading metrics."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.STANDARD):
        self.mode = mode

    def calculate_overtrading_metric(self, trades_df) -> Dict[str, Any]:
        """
        Calculates overtrading metrics based on trade frequency and volume spikes.
        Standard lightweight implementation using Pandas/NumPy.
        """
        if trades_df.empty:
            return {"overtrading_index": 0.0, "risk_level": "LOW", "trade_count": 0}

        trade_count = len(trades_df)
        overtrading_index = min(100.0, (trade_count / 10.0) * 20.0)

        risk_level = "LOW"
        if overtrading_index > 70:
            risk_level = "HIGH"
        elif overtrading_index > 40:
            risk_level = "MODERATE"

        return {
            "overtrading_index": overtrading_index,
            "risk_level": risk_level,
            "trade_count": trade_count,
            "mode": self.mode.value
        }


def launch_gui():
    """Initializes and runs the PySide6 desktop window interface."""
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QComboBox, QTextEdit, QStatusBar
    )
    from PySide6.QtCore import Qt

    class PSXMainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.db_manager = DatabaseManager()
            self.current_mode = ExecutionMode.STANDARD
            self.image_processor = SequentialImageProcessor(mode=self.current_mode)
            self.analyzer = PriceActionAnalyzer(mode=self.current_mode)
            self.init_ui()

        def init_ui(self):
            self.setWindowTitle("PSX Price Action & Overtrading Analysis Tool (Lightweight)")
            self.resize(750, 500)

            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)

            # Header & Mode Selection
            top_bar = QHBoxLayout()
            title_label = QLabel("<h2>PSX Trading Analyzer</h2>")
            top_bar.addWidget(title_label)
            top_bar.addStretch()

            mode_label = QLabel("Execution Mode:")
            self.mode_combo = QComboBox()
            self.mode_combo.addItems([ExecutionMode.STANDARD.value, ExecutionMode.ADVANCED.value])
            self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
            top_bar.addWidget(mode_label)
            top_bar.addWidget(self.mode_combo)

            layout.addLayout(top_bar)

            # Console / Output display
            self.output_text = QTextEdit()
            self.output_text.setReadOnly(True)
            self.output_text.setText(
                "Welcome to PSX Price Action & Overtrading Analysis Tool.\n"
                "Target Architecture: CPU-first (Intel i5-4210U), 8GB RAM.\n"
                "Sequential Processing: Enabled.\n\n"
                "Ready for operational tasks."
            )
            layout.addWidget(self.output_text)

            # Action Buttons
            btn_layout = QHBoxLayout()

            self.btn_run_analysis = QPushButton("Run Sample Price Action Analysis")
            self.btn_run_analysis.clicked.connect(self.run_sample_analysis)
            btn_layout.addWidget(self.btn_run_analysis)

            self.btn_check_mem = QPushButton("Check Memory Footprint")
            self.btn_check_mem.clicked.connect(self.check_memory)
            btn_layout.addWidget(self.btn_check_mem)

            layout.addLayout(btn_layout)

            # Status bar
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
            self.update_status_bar()

            self.setCentralWidget(central_widget)

        def on_mode_changed(self, selected_mode_text: str):
            if selected_mode_text == ExecutionMode.ADVANCED.value:
                self.current_mode = ExecutionMode.ADVANCED
                self.append_log("[INFO] Switched to Advanced Mode (Placeholder for high-tier hardware).")
            else:
                self.current_mode = ExecutionMode.STANDARD
                self.append_log("[INFO] Switched to Standard Mode (Optimized for Intel i5-4210U).")

            self.image_processor.mode = self.current_mode
            self.analyzer.mode = self.current_mode
            self.update_status_bar()

        def append_log(self, text: str):
            self.output_text.append(text)

        def update_status_bar(self):
            mem_mb = MemoryMonitor.get_memory_usage_mb()
            self.status_bar.showMessage(f"Mode: {self.current_mode.value} | RSS Memory: {mem_mb:.1f} MB | CPU-Only Execution")

        def run_sample_analysis(self):
            import pandas as pd
            sample_data = pd.DataFrame([
                {"symbol": "KSE100", "price": 65000.0, "volume": 10000},
                {"symbol": "KSE100", "price": 65150.0, "volume": 12000},
                {"symbol": "KSE100", "price": 64900.0, "volume": 15000},
            ])
            res = self.analyzer.calculate_overtrading_metric(sample_data)
            self.append_log(f"[ANALYSIS RESULT] Overtrading Score: {res['overtrading_index']} | Risk: {res['risk_level']} | Mode: {res['mode']}")
            self.update_status_bar()

        def check_memory(self):
            mem_mb = MemoryMonitor.get_memory_usage_mb()
            self.append_log(f"[MEMORY CHECK] Current Process Memory: {mem_mb:.2f} MB")
            self.update_status_bar()

    app = QApplication(sys.argv)
    window = PSXMainWindow()
    window.show()
    return app.exec()


def main():
    if "--headless" in sys.argv:
        logger.info("Running in headless verification mode...")
        db = DatabaseManager(":memory:")
        db.log_trade("OGDC", "2023-10-25 10:00:00", 105.5, 5000, "BUY")
        logger.info(f"Headless test completed. Logged trades: {db.get_trade_count()}")
        logger.info(f"Memory footprint: {MemoryMonitor.get_memory_usage_mb():.2f} MB")
        return 0
    else:
        return launch_gui()


if __name__ == "__main__":
    sys.exit(main())
