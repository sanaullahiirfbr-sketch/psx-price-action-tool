"""
Lightweight resource monitoring diagnostic component.
Tracks CPU %, RAM usage, processing stage timers, and handles memory cleanup.
"""

import gc
import time
import psutil
from typing import Dict, Any


class ResourceMonitor:
    """Monitors CPU and RAM consumption and timings for hardware-aware diagnosis."""

    def __init__(self):
        self.process = psutil.Process()
        self.stage_start_time = None
        self.current_stage = None

    def get_system_metrics(self) -> Dict[str, Any]:
        """Returns current CPU and RAM usage for process and overall system."""
        try:
            mem_info = self.process.memory_info()
            process_ram_mb = mem_info.rss / (1024 * 1024)
        except Exception:
            process_ram_mb = 0.0

        sys_mem = psutil.virtual_memory()

        return {
            "process_ram_mb": round(process_ram_mb, 2),
            "system_ram_used_gb": round(sys_mem.used / (1024 ** 3), 2),
            "system_ram_total_gb": round(sys_mem.total / (1024 ** 3), 2),
            "system_ram_percent": sys_mem.percent,
            "cpu_percent": psutil.cpu_percent(interval=None),
        }

    def start_stage_timer(self, stage_name: str):
        """Starts timing a processing stage."""
        self.current_stage = stage_name
        self.stage_start_time = time.time()

    def end_stage_timer(self) -> float:
        """Returns elapsed time in seconds for current stage."""
        if self.stage_start_time is None:
            return 0.0
        elapsed = time.time() - self.stage_start_time
        self.stage_start_time = None
        self.current_stage = None
        return round(elapsed, 3)

    @staticmethod
    def release_memory():
        """Triggers explicit garbage collection to release unused image objects."""
        gc.collect()
