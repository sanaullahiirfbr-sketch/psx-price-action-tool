"""
SQLite Database Storage Manager and Thumbnail Cache.
Stores extracted numerical data, layout metadata, and thumbnail image paths on disk
to avoid keeping full-resolution image matrices in RAM (Section 80).
"""

import sqlite3
import json
import os
import cv2
import numpy as np
from typing import Dict, Any, List, Optional


class StorageManager:
    """Manages persistent SQLite storage and thumbnail cache."""

    def __init__(self, db_path: str = "psx_analyzer.db", cache_dir: str = "cache"):
        self.db_path = db_path
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates database tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    thumbnail_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'PENDING',
                    ocr_data_json TEXT,
                    vision_data_json TEXT,
                    patterns_json TEXT,
                    report_json TEXT
                )
            """)
            conn.commit()

    def generate_and_save_thumbnail(self, image_path: str, thumbnail_size=(250, 250)) -> Optional[str]:
        """Generates a thumbnail and saves it to cache directory, returning thumbnail file path."""
        if not os.path.exists(image_path):
            return None

        img = cv2.imread(image_path)
        if img is None:
            return None

        # Resize preserving aspect ratio
        h, w = img.shape[:2]
        target_w, target_h = thumbnail_size
        scale = min(target_w / float(w), target_h / float(h))
        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        filename = f"thumb_{os.path.basename(image_path)}"
        thumb_path = os.path.join(self.cache_dir, filename)
        cv2.imwrite(thumb_path, resized)

        # Free image objects
        del img
        del resized

        return thumb_path

    def save_analysis_record(self, file_path: str, status: str, ocr_data: Dict[str, Any],
                             vision_data: Dict[str, Any], patterns: List[Dict[str, Any]],
                             report: Dict[str, Any], thumbnail_path: Optional[str] = None):
        """Saves or updates analysis results in SQLite database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO image_records (file_path, thumbnail_path, status, ocr_data_json, vision_data_json, patterns_json, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    thumbnail_path=COALESCE(EXCLUDED.thumbnail_path, thumbnail_path),
                    status=EXCLUDED.status,
                    ocr_data_json=EXCLUDED.ocr_data_json,
                    vision_data_json=EXCLUDED.vision_data_json,
                    patterns_json=EXCLUDED.patterns_json,
                    report_json=EXCLUDED.report_json
            """, (
                file_path,
                thumbnail_path,
                status,
                json.dumps(ocr_data),
                json.dumps(vision_data),
                json.dumps(patterns),
                json.dumps(report)
            ))
            conn.commit()

    def get_record(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Retrieves record for a specific image file."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM image_records WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row["id"],
                "file_path": row["file_path"],
                "thumbnail_path": row["thumbnail_path"],
                "status": row["status"],
                "ocr_data": json.loads(row["ocr_data_json"]) if row["ocr_data_json"] else {},
                "vision_data": json.loads(row["vision_data_json"]) if row["vision_data_json"] else {},
                "patterns": json.loads(row["patterns_json"]) if row["patterns_json"] else [],
                "report": json.loads(row["report_json"]) if row["report_json"] else {},
            }

    def get_all_records(self) -> List[Dict[str, Any]]:
        """Retrieves all image records from database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM image_records ORDER BY id ASC")
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "file_path": row["file_path"],
                    "thumbnail_path": row["thumbnail_path"],
                    "status": row["status"],
                    "ocr_data": json.loads(row["ocr_data_json"]) if row["ocr_data_json"] else {},
                    "vision_data": json.loads(row["vision_data_json"]) if row["vision_data_json"] else {},
                    "patterns": json.loads(row["patterns_json"]) if row["patterns_json"] else [],
                    "report": json.loads(row["report_json"]) if row["report_json"] else {},
                })
            return results
