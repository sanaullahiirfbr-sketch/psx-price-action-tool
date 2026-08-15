"""
Abstract modular engine interfaces to support hardware scalability (Section 92).
Enables seamless plugging of advanced GPU / cloud engines in the future while keeping default CPU implementations intact.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import numpy as np


class BaseOCREngine(ABC):
    """Abstract interface for text / numerical extraction engine."""

    @abstractmethod
    def extract_text(self, image_region: np.ndarray) -> Dict[str, Any]:
        """Extract text and numerical values from given image region."""
        pass


class BaseVisionEngine(ABC):
    """Abstract interface for computer-vision and region crop engine."""

    @abstractmethod
    def detect_chart_region(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect layout, chart area, legend, and indicator panels."""
        pass


class BasePatternEngine(ABC):
    """Abstract interface for candlestick pattern recognition engine."""

    @abstractmethod
    def analyze_candlesticks(self, chart_region: np.ndarray) -> List[Dict[str, Any]]:
        """Identify candlestick geometry, bodies, wicks, and patterns."""
        pass


class BaseAIEngine(ABC):
    """Abstract interface for higher-level AI / technical reasoning engine."""

    @abstractmethod
    def evaluate_setup(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize technical indicators and price action into analysis insights."""
        pass
