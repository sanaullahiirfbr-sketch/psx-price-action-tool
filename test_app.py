"""
Comprehensive unit test suite for PSX Technical Analyzer.
Tests performance modes, diagnostic resource monitoring, database storage,
CPU engines, sequential processing pipeline, validation, and fallback degradation.
"""

import os
import pytest
import numpy as np
import cv2

from config import AppConfig, PerformanceMode
from diagnostics import ResourceMonitor
from storage import StorageManager
from engines import DefaultCPUVisionEngine, DefaultCPUOCREngine, DefaultCPUPatternEngine, DefaultCPUAIEngine
from validation import DataValidator, ReportGenerator
from pipeline import ProcessingPipeline


@pytest.fixture
def sample_image_path(tmp_path):
    """Creates a dummy sample chart image for testing."""
    img_path = str(tmp_path / "test_chart.png")
    # Create 800x600 synthetic image with green and red rectangles
    img = np.zeros((600, 800, 3), dtype=np.uint8) + 200
    cv2.rectangle(img, (100, 100), (200, 400), (0, 200, 0), -1)  # Green candle
    cv2.rectangle(img, (250, 150), (350, 350), (0, 0, 200), -1)  # Red candle
    cv2.imwrite(img_path, img)
    return img_path


def test_app_config():
    config = AppConfig(PerformanceMode.STANDARD)
    assert config.mode == PerformanceMode.STANDARD
    assert config.max_image_dim == 1280
    assert config.sequential_processing is True

    config.set_mode(PerformanceMode.ADVANCED)
    assert config.mode == PerformanceMode.ADVANCED
    assert config.max_image_dim == 2560


def test_resource_monitor():
    monitor = ResourceMonitor()
    metrics = monitor.get_system_metrics()
    assert "process_ram_mb" in metrics
    assert "cpu_percent" in metrics

    monitor.start_stage_timer("Test Stage")
    assert monitor.current_stage == "Test Stage"
    elapsed = monitor.end_stage_timer()
    assert elapsed >= 0.0


def test_storage_manager(tmp_path, sample_image_path):
    db_file = str(tmp_path / "test.db")
    cache_dir = str(tmp_path / "cache")
    storage = StorageManager(db_path=db_file, cache_dir=cache_dir)

    thumb_path = storage.generate_and_save_thumbnail(sample_image_path, (100, 100))
    assert thumb_path is not None
    assert os.path.exists(thumb_path)

    ocr_data = {"confidence": 0.85, "values": {"rsi": 55, "last_price": 100}}
    storage.save_analysis_record(
        file_path=sample_image_path,
        status="OK",
        ocr_data=ocr_data,
        vision_data={"status": "success"},
        patterns=[{"pattern": "Bullish"}],
        report={"summary": "Test Report"},
        thumbnail_path=thumb_path
    )

    record = storage.get_record(sample_image_path)
    assert record is not None
    assert record["status"] == "OK"
    assert record["ocr_data"]["values"]["rsi"] == 55


def test_cpu_engines(sample_image_path):
    img = cv2.imread(sample_image_path)

    vision_engine = DefaultCPUVisionEngine()
    vision_res = vision_engine.detect_chart_region(img)
    assert vision_res["status"] == "success"
    assert "chart_bbox" in vision_res

    ocr_engine = DefaultCPUOCREngine()
    ocr_res = ocr_engine.extract_text(img)
    assert ocr_res["confidence"] > 0

    pattern_engine = DefaultCPUPatternEngine()
    patterns = pattern_engine.analyze_candlesticks(img)
    assert isinstance(patterns, list)

    ai_engine = DefaultCPUAIEngine()
    ai_res = ai_engine.evaluate_setup({"ocr_data": ocr_res, "patterns": patterns})
    assert "bias" in ai_res


def test_data_validation():
    # Test valid data
    valid_ocr = {"confidence": 0.90, "values": {"rsi": 65.5, "last_price": 250.0}}
    validated, warnings = DataValidator.validate_ocr_data(valid_ocr)
    assert validated["status"] == "OK"
    assert len(warnings) == 0

    # Test invalid RSI out of bounds
    invalid_ocr = {"confidence": 0.50, "values": {"rsi": 150.0, "last_price": -10.0}}
    validated, warnings = DataValidator.validate_ocr_data(invalid_ocr)
    assert validated["status"] == "Not reliably extracted"
    assert len(warnings) > 0


def test_processing_pipeline(tmp_path, sample_image_path):
    db_file = str(tmp_path / "pipeline_test.db")
    cache_dir = str(tmp_path / "cache")
    config = AppConfig(PerformanceMode.STANDARD)
    storage = StorageManager(db_path=db_file, cache_dir=cache_dir)
    monitor = ResourceMonitor()

    pipeline = ProcessingPipeline(config, storage, monitor)
    progress_updates = []

    def on_progress(current, total, stage, metrics):
        progress_updates.append((current, total, stage))

    results = pipeline.process_images([sample_image_path], progress_callback=on_progress)

    assert len(results) == 1
    assert results[0]["file_path"] == sample_image_path
    assert len(progress_updates) > 0
