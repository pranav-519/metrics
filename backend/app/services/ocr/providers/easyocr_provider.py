import os
import time
from typing import Optional, List, Dict, Any

from app.services.ocr.base import BaseOCREngine, OCRResult, OCRBoxResult
from app.core.config import settings

class EasyOCREngine(BaseOCREngine):
    """
    Optional secondary OCR Provider using EasyOCR (PyTorch).
    Initialized on demand if installed.
    """

    def __init__(self):
        self.engine_name = "EasyOCR-Pretrained"
        self._reader = None
        self._init_error = None
        self._init_engine()

    def _init_engine(self):
        try:
            import easyocr  # type: ignore
            self._reader = easyocr.Reader(['en'], gpu=False)
            self._init_error = None
        except Exception as e:
            self._reader = None
            self._init_error = str(e)

    def is_available(self) -> bool:
        return self._reader is not None

    def extract_text(
        self,
        image_path: str,
        image_id: Optional[int] = None,
        image_type: Optional[str] = "FRONT",
        confidence_threshold: Optional[float] = None,
        **kwargs
    ) -> OCRResult:
        start_time = time.time()
        threshold = confidence_threshold if confidence_threshold is not None else settings.OCR_CONFIDENCE_THRESHOLD

        if not self.is_available():
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"EasyOCR is not installed or available: {self._init_error}",
                processing_time_ms=0.0
            )

        try:
            import cv2
            img = cv2.imread(image_path)
            img_h, img_w = img.shape[:2] if img is not None else (0, 0)
            results = self._reader.readtext(image_path)
        except Exception as e:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"EasyOCR inference error: {str(e)}",
                processing_time_ms=round((time.time() - start_time) * 1000.0, 2)
            )

        elapsed_ms = round((time.time() - start_time) * 1000.0, 2)

        if not results:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                total_detections=0,
                average_confidence=0.0,
                engine_name=self.engine_name,
                processing_time_ms=elapsed_ms,
                status="NO_TEXT_DETECTED"
            )

        boxes: List[OCRBoxResult] = []
        confidences: List[float] = []
        text_lines: List[str] = []
        high_conf_count = 0

        for idx, (bbox, text, conf) in enumerate(results):
            if not text or not text.strip():
                continue

            cleaned_text = text.strip()
            score = float(conf)
            confidences.append(score)
            text_lines.append(cleaned_text)

            if score >= threshold:
                high_conf_count += 1

            xs = [float(p[0]) for p in bbox]
            ys = [float(p[1]) for p in bbox]
            x1, y1 = int(round(min(xs))), int(round(min(ys)))
            x2, y2 = int(round(max(xs))), int(round(max(ys)))
            x, y = max(0, x1), max(0, y1)
            w, h = max(0, x2 - x1), max(0, y2 - y1)

            bbox_dict = {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "x_rel": round(x / max(img_w, 1), 4),
                "y_rel": round(y / max(img_h, 1), 4),
                "w_rel": round(w / max(img_w, 1), 4),
                "h_rel": round(h / max(img_h, 1), 4),
                "polygon": [[round(float(p[0]), 1), round(float(p[1]), 1)] for p in bbox]
            }

            boxes.append(OCRBoxResult(
                text=cleaned_text,
                confidence=round(score, 4),
                bounding_box=bbox_dict,
                line_number=idx + 1,
                image_id=image_id,
                image_type=image_type
            ))

        avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        return OCRResult(
            image_id=image_id,
            image_type=image_type,
            full_text="\n".join(text_lines),
            boxes=boxes,
            total_detections=len(boxes),
            average_confidence=avg_conf,
            min_confidence=round(min(confidences), 4) if confidences else 0.0,
            max_confidence=round(max(confidences), 4) if confidences else 0.0,
            high_confidence_count=high_conf_count,
            engine_name=self.engine_name,
            processing_time_ms=elapsed_ms,
            status="COMPLETED"
        )
