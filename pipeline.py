"""
Sequential image processing pipeline with cancellation support and memory optimization.
Processes images strictly one-by-one (Section 80/82/83).
"""

import cv2
import os
import numpy as np
from typing import List, Callable, Optional, Dict, Any

from config import AppConfig
from diagnostics import ResourceMonitor
from engines import DefaultCPUVisionEngine, DefaultCPUOCREngine, DefaultCPUPatternEngine, DefaultCPUAIEngine
from storage import StorageManager
from validation import DataValidator, ReportGenerator


class ProcessingPipeline:
    """Sequential image analysis pipeline optimized for CPU and low RAM."""

    def __init__(self, config: AppConfig, storage: StorageManager, monitor: ResourceMonitor):
        self.config = config
        self.storage = storage
        self.monitor = monitor

        # Modular engines
        self.vision_engine = DefaultCPUVisionEngine()
        self.ocr_engine = DefaultCPUOCREngine()
        self.pattern_engine = DefaultCPUPatternEngine()
        self.ai_engine = DefaultCPUAIEngine()

        self.is_cancelled = False

    def cancel(self):
        """Signals cancellation request from user interface."""
        self.is_cancelled = True

    def process_images(self, file_paths: List[str],
                       progress_callback: Optional[Callable[[int, int, str, Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """
        Sequentially processes a batch of image file paths.
        Calls progress_callback(current_idx, total, stage_description, resource_metrics).
        """
        self.is_cancelled = False
        results = []
        total = len(file_paths)

        for idx, file_path in enumerate(file_paths, start=1):
            if self.is_cancelled:
                break

            record = self._process_single_image(idx, total, file_path, progress_callback)
            results.append(record)

            # Explicit garbage collection after each image (Section 80)
            if self.config.force_gc_after_each_image:
                self.monitor.release_memory()

        return results

    def _process_single_image(self, idx: int, total: int, file_path: str,
                              progress_callback: Optional[Callable[[int, int, str, Dict[str, Any]], None]]) -> Dict[str, Any]:
        """Executes full sequential processing stages for a single image."""

        # Helper notify
        def notify(stage_name: str):
            if progress_callback:
                metrics = self.monitor.get_system_metrics()
                progress_callback(idx, total, stage_name, metrics)

        # Stage 1: Quality Check & Loading
        self.monitor.start_stage_timer("Image Loading & Quality Check")
        notify("Quality Check & Image Loading")

        if not os.path.exists(file_path):
            error_report = {"status": "ERROR", "summary_text": "File not found"}
            self.storage.save_analysis_record(file_path, "ERROR", {}, {}, [], error_report, None)
            return {"file_path": file_path, "status": "ERROR"}

        # Generate thumbnail for GUI / Cache
        thumb_path = self.storage.generate_and_save_thumbnail(file_path, self.config.thumbnail_size)

        img = cv2.imread(file_path)
        if img is None:
            error_report = {"status": "ERROR", "summary_text": "Failed to decode image"}
            self.storage.save_analysis_record(file_path, "ERROR", {}, {}, [], error_report, thumb_path)
            return {"file_path": file_path, "status": "ERROR"}

        # Downscale oversized image if above threshold (Section 82)
        h, w = img.shape[:2]
        max_dim = self.config.max_image_dim
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        if self.is_cancelled:
            del img
            return {"file_path": file_path, "status": "CANCELLED"}

        # Stage 2: Chart Region Detection
        self.monitor.start_stage_timer("Chart Region Detection")
        notify("Detecting chart region and layout...")
        vision_data = self.vision_engine.detect_chart_region(img)

        # Stage 3: Region Cropping & OCR
        self.monitor.start_stage_timer("Indicator OCR Extraction")
        notify("Extracting indicator values via OCR...")
        chart_bbox = vision_data.get("chart_bbox", [0, 0, img.shape[0], img.shape[1]])

        # Crop region for indicator panel / chart area
        y1, x1, y2, x2 = chart_bbox
        cropped_region = img[y1:y2, x1:x2] if (y2 > y1 and x2 > x1) else img

        raw_ocr_data = self.ocr_engine.extract_text(cropped_region)

        # Stage 4: Candlestick Pattern Analysis
        self.monitor.start_stage_timer("Candlestick Pattern Recognition")
        notify("Analyzing candlestick geometry and patterns...")
        patterns = self.pattern_engine.analyze_candlesticks(cropped_region)

        # Stage 5: Numerical Validation
        self.monitor.start_stage_timer("Numerical Validation")
        notify("Validating extracted data...")
        validated_ocr, warnings = DataValidator.validate_ocr_data(raw_ocr_data)

        # Stage 6: AI / Technical Evaluation
        self.monitor.start_stage_timer("Technical Evaluation")
        notify("Generating technical analysis report...")
        extracted_data = {"ocr_data": validated_ocr, "patterns": patterns}
        ai_eval = self.ai_engine.evaluate_setup(extracted_data)

        report = ReportGenerator.generate_report(file_path, validated_ocr, patterns, ai_eval)

        status = validated_ocr.get("status", "COMPLETED")

        # Save to SQLite storage
        self.storage.save_analysis_record(
            file_path=file_path,
            status=status,
            ocr_data=validated_ocr,
            vision_data=vision_data,
            patterns=patterns,
            report=report,
            thumbnail_path=thumb_path
        )

        # Crucial Memory Release: Explicitly delete image array objects
        del img
        del cropped_region

        return {
            "file_path": file_path,
            "thumbnail_path": thumb_path,
            "status": status,
            "ocr_data": validated_ocr,
            "vision_data": vision_data,
            "patterns": patterns,
            "report": report
        }
