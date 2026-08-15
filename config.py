"""
Configuration settings and performance modes optimized for HP Notebook i5-4210U (8GB RAM, CPU-first).
"""

import os
from enum import Enum


class PerformanceMode(Enum):
    STANDARD = "STANDARD"      # Lightweight CPU-first mode optimized for 8GB RAM dual-core laptop
    ADVANCED = "ADVANCED"      # High accuracy mode for more powerful hardware or cloud backends


class AppConfig:
    """Hardware-aware application configuration."""

    def __init__(self, mode: PerformanceMode = PerformanceMode.STANDARD):
        self.mode = mode

        # Memory Management Thresholds
        self.max_ram_mb = 2500            # Limit target for application memory consumption (MB)
        self.sequential_processing = True # Always process screenshots one-by-one to avoid RAM spikes
        self.lazy_image_loading = True    # Keep paths, load original images only when needed
        self.force_gc_after_each_image = True # Trigger explicit Python garbage collection

        # Image Downscaling & Crop Constraints
        # Protects CPU and RAM from oversized 4K/retina TradingView screenshots
        if self.mode == PerformanceMode.STANDARD:
            self.max_image_dim = 1280     # Max width/height during computer-vision analysis
            self.thumbnail_size = (250, 250)
            self.use_heavy_ocr = False
        else:
            self.max_image_dim = 2560
            self.thumbnail_size = (400, 400)
            self.use_heavy_ocr = True

        # Database Storage
        self.db_path = os.path.abspath("psx_analyzer.db")

    def set_mode(self, mode: PerformanceMode):
        self.mode = mode
        if self.mode == PerformanceMode.STANDARD:
            self.max_image_dim = 1280
            self.thumbnail_size = (250, 250)
            self.use_heavy_ocr = False
        else:
            self.max_image_dim = 2560
            self.thumbnail_size = (400, 400)
            self.use_heavy_ocr = True

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "max_ram_mb": self.max_ram_mb,
            "max_image_dim": self.max_image_dim,
            "sequential_processing": self.sequential_processing,
            "lazy_image_loading": self.lazy_image_loading,
            "thumbnail_size": self.thumbnail_size,
            "db_path": self.db_path,
        }
