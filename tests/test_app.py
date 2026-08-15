"""
Unit tests for PSX Price Action & Overtrading Analysis Tool.
Verifies database operations, two-tier mode, sequential image processing, and low memory consumption.
"""

import os
import pytest
import pandas as pd
from PIL import Image

from app import (
    ExecutionMode,
    MemoryMonitor,
    DatabaseManager,
    SequentialImageProcessor,
    PriceActionAnalyzer,
)


def test_database_manager(tmp_path):
    db_file = tmp_path / "test_psx.db"
    db = DatabaseManager(str(db_file))

    assert db.get_trade_count() == 0
    db.log_trade("ENGRO", "2023-10-25 10:30:00", 280.5, 1000, "BUY", 15.0)
    assert db.get_trade_count() == 1


def test_execution_modes():
    processor_std = SequentialImageProcessor(mode=ExecutionMode.STANDARD)
    processor_adv = SequentialImageProcessor(mode=ExecutionMode.ADVANCED)

    assert processor_std.mode == ExecutionMode.STANDARD
    assert processor_adv.mode == ExecutionMode.ADVANCED


def test_sequential_image_processor(tmp_path):
    img_path1 = tmp_path / "test1.png"
    img_path2 = tmp_path / "test2.png"

    # Create dummy images
    Image.new("RGB", (100, 100), color="blue").save(img_path1)
    Image.new("RGB", (200, 200), color="red").save(img_path2)

    processor = SequentialImageProcessor(mode=ExecutionMode.STANDARD)
    results = processor.process_batch_sequentially([str(img_path1), str(img_path2)])

    assert len(results) == 2
    assert results[0]["status"] == "success"
    assert results[0]["width"] == 100
    assert results[1]["status"] == "success"
    assert results[1]["width"] == 200


def test_price_action_analyzer():
    analyzer = PriceActionAnalyzer(mode=ExecutionMode.STANDARD)
    empty_res = analyzer.calculate_overtrading_metric(pd.DataFrame())
    assert empty_res["overtrading_index"] == 0.0
    assert empty_res["risk_level"] == "LOW"

    sample_df = pd.DataFrame([{"symbol": "SYS", "price": 400.0, "volume": 500}] * 25)
    res = analyzer.calculate_overtrading_metric(sample_df)
    assert res["overtrading_index"] > 40.0


def test_memory_footprint():
    mem_mb = MemoryMonitor.get_memory_usage_mb()
    # Ensure memory footprint during test execution stays well below 500 MB (Target constraint: < 2-3 GB available)
    assert mem_mb < 500.0
