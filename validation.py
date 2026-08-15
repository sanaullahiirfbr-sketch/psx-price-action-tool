"""
Data validation and numerical cross-checking utilities.
Implements sanity checks, low-confidence degradation flags, and explainable reporting.
"""

from typing import Dict, Any, List, Tuple


class DataValidator:
    """Validates extracted numerical indicators and chart metadata."""

    @staticmethod
    def validate_ocr_data(ocr_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validates values extracted by OCR engine.
        Returns cleaned data dictionary and list of validation warnings/flags.
        """
        warnings = []
        cleaned_values = dict(ocr_data.get("values", {}))

        # Check RSI bounds (0-100)
        rsi = cleaned_values.get("rsi")
        if rsi is not None:
            try:
                rsi_val = float(rsi)
                if not (0 <= rsi_val <= 100):
                    warnings.append(f"Invalid RSI value {rsi_val} (outside 0-100 range). Flagged.")
                    cleaned_values["rsi"] = None
            except ValueError:
                warnings.append(f"Non-numeric RSI string '{rsi}'. Flagged.")
                cleaned_values["rsi"] = None

        # Check Price (>0)
        price = cleaned_values.get("last_price")
        if price is not None:
            try:
                price_val = float(price)
                if price_val <= 0:
                    warnings.append(f"Invalid stock price {price_val} (<= 0). Flagged.")
                    cleaned_values["last_price"] = None
            except ValueError:
                warnings.append(f"Non-numeric price string '{price}'. Flagged.")
                cleaned_values["last_price"] = None

        # Low confidence fallback flag (Section 89)
        confidence = ocr_data.get("confidence", 0.0)
        status = "OK"
        if confidence < 0.70 or any(v is None for v in cleaned_values.values()):
            status = "Not reliably extracted"
            warnings.append("Low confidence or missing fields detected. Manual correction recommended.")

        validated_ocr = dict(ocr_data)
        validated_ocr["values"] = cleaned_values
        validated_ocr["status"] = status
        validated_ocr["warnings"] = warnings

        return validated_ocr, warnings


class ReportGenerator:
    """Generates human-readable, explainable technical analysis reports."""

    @staticmethod
    def generate_report(file_path: str, validated_ocr: Dict[str, Any],
                        patterns: List[Dict[str, Any]], ai_eval: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizes all extraction results into structured report object."""
        values = validated_ocr.get("values", {})
        warnings = validated_ocr.get("warnings", [])
        status = validated_ocr.get("status", "OK")

        price_str = f"PKR {values.get('last_price')}" if values.get('last_price') is not None else "Not reliably extracted"
        rsi_str = f"{values.get('rsi')}" if values.get('rsi') is not None else "Not reliably extracted"

        pattern_summary = ", ".join([p.get("pattern", "") for p in patterns]) if patterns else "None detected"

        summary_text = (
            f"Image Analysis Report for {file_path}:\n"
            f"- Symbol/Timeframe: {values.get('symbol', 'PSX')} ({values.get('timeframe', '1D')})\n"
            f"- Price: {price_str}\n"
            f"- RSI Indicator: {rsi_str}\n"
            f"- Candlestick Patterns: {pattern_summary}\n"
            f"- Technical Bias: {ai_eval.get('bias', 'NEUTRAL')}\n"
            f"- Status: {status}\n"
        )

        return {
            "summary_text": summary_text,
            "bias": ai_eval.get("bias", "NEUTRAL"),
            "key_reasons": ai_eval.get("key_reasons", []),
            "warnings": warnings,
            "status": status,
            "values": values,
            "patterns": patterns,
        }
