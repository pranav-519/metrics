import os
import time
import threading
from typing import Optional, List, Dict, Any
import cv2
import numpy as np
from PIL import Image

from app.services.ocr.base import BaseOCREngine, OCRResult, OCRBoxResult
from app.core.config import settings

# Global shared lock and instance for lazy singleton initialization
_paddle_lock = threading.Lock()
_shared_paddle_engine = None
_shared_init_error: Optional[str] = None


class PaddleOCRProvider(BaseOCREngine):
    """
    Primary Pre-Trained OCR Engine powered by PaddleOCR PP-OCRv6.
    
    Extracts real packaging text tokens, fine-grained bounding boxes,
    and recognition confidences from packaged commodity imagery.
    Never fabricates or hallucinates text.
    """

    def __init__(
        self,
        ocr_version: Optional[str] = None,
        lang: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.engine_name = "PaddleOCR-PP-OCRv6"
        self.ocr_version = ocr_version or getattr(settings, "OCR_MODEL", "PP-OCRv6")
        self.lang = lang or getattr(settings, "OCR_LANGUAGE", "en")
        self.device = device or getattr(settings, "OCR_DEVICE", "cpu")
        self._ensure_engine_initialized()

    def _ensure_engine_initialized(self):
        global _shared_paddle_engine, _shared_init_error
        if _shared_paddle_engine is not None:
            return

        with _paddle_lock:
            if _shared_paddle_engine is not None:
                return
            try:
                # Bypass remote hoster connectivity checks to speed up startup
                os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
                
                from paddleocr import PaddleOCR
                
                # In PaddleOCR 3.7.0 on Windows CPU, enable_mkldnn=False avoids PIR oneDNN
                # ConvertPirAttribute2RuntimeAttribute incompatibility.
                # Disabling doc unwarping and doc orientation prevents loading 3D page flattening (UVDoc)
                # while textline orientation handles 90/180/270 rotated label text.
                _shared_paddle_engine = PaddleOCR(
                    ocr_version=self.ocr_version,
                    lang=self.lang,
                    device=self.device,
                    enable_mkldnn=False,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=True,
                )
                _shared_init_error = None
            except Exception as e:
                _shared_paddle_engine = None
                _shared_init_error = str(e)

    def is_available(self) -> bool:
        return _shared_paddle_engine is not None

    @property
    def init_error(self) -> Optional[str]:
        return _shared_init_error

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

        if not os.path.exists(image_path):
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"Image file not found at path: {image_path}",
                processing_time_ms=0.0
            )

        if not self.is_available():
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"PaddleOCR PP-OCRv6 initialization failed: {self.init_error}",
                processing_time_ms=0.0
            )

        # Determine image dimensions reliably using cv2 or PIL
        try:
            img = cv2.imread(image_path)
            if img is None:
                pil_img = Image.open(image_path)
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            img_h, img_w = img.shape[:2]
        except Exception as e:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"Could not load image dimensions: {str(e)}",
                processing_time_ms=round((time.time() - start_time) * 1000.0, 2)
            )

        # Run PaddleOCR inference
        try:
            # predict accepts path or numpy array
            predictions = _shared_paddle_engine.predict(image_path)
        except Exception as e:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"PaddleOCR inference error: {str(e)}",
                processing_time_ms=round((time.time() - start_time) * 1000.0, 2)
            )

        elapsed_ms = round((time.time() - start_time) * 1000.0, 2)

        # Handle empty detection
        if not predictions or len(predictions) == 0:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                total_detections=0,
                average_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
                high_confidence_count=0,
                engine_name=self.engine_name,
                processing_time_ms=elapsed_ms,
                status="NO_TEXT_DETECTED"
            )

        first_pred = predictions[0]
        rec_texts = first_pred.get("rec_texts", [])
        rec_scores = first_pred.get("rec_scores", [])
        rec_polys = first_pred.get("rec_polys", [])

        if not rec_texts:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                total_detections=0,
                average_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
                high_confidence_count=0,
                engine_name=self.engine_name,
                processing_time_ms=elapsed_ms,
                status="NO_TEXT_DETECTED"
            )

        boxes: List[OCRBoxResult] = []
        confidences: List[float] = []
        text_lines: List[str] = []
        high_conf_count = 0

        for idx, (raw_text, raw_score, poly) in enumerate(zip(rec_texts, rec_scores, rec_polys)):
            if raw_text is None:
                continue
            cleaned_text = str(raw_text).strip()
            if not cleaned_text:
                continue

            conf = float(raw_score)
            # Ensure confidence is clamped between 0.0 and 1.0
            conf = max(0.0, min(1.0, conf))
            confidences.append(conf)
            text_lines.append(cleaned_text)

            if conf >= threshold:
                high_conf_count += 1

            # Convert polygon into axis-aligned bbox and normalized relative coordinates
            # poly is an array/list of 2D points [[x, y], ...]
            poly_pts = []
            xs = []
            ys = []
            for pt in poly:
                px = float(pt[0])
                py = float(pt[1])
                # Clamp coordinates to image dimensions
                px_clamped = max(0.0, min(float(img_w), px))
                py_clamped = max(0.0, min(float(img_h), py))
                xs.append(px_clamped)
                ys.append(py_clamped)
                poly_pts.append([round(px, 1), round(py, 1)])

            if not xs or not ys:
                continue

            x1 = int(round(min(xs)))
            y1 = int(round(min(ys)))
            x2 = int(round(max(xs)))
            y2 = int(round(max(ys)))
            x = max(0, x1)
            y = max(0, y1)
            w = max(0, x2 - x1)
            h = max(0, y2 - y1)

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
                "polygon": poly_pts
            }

            boxes.append(OCRBoxResult(
                text=cleaned_text,
                confidence=round(conf, 4),
                bounding_box=bbox_dict,
                line_number=idx + 1,
                image_id=image_id,
                image_type=image_type
            ))

        if not boxes:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                total_detections=0,
                average_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
                high_confidence_count=0,
                engine_name=self.engine_name,
                processing_time_ms=elapsed_ms,
                status="NO_TEXT_DETECTED"
            )

        avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        min_conf = round(min(confidences), 4) if confidences else 0.0
        max_conf = round(max(confidences), 4) if confidences else 0.0

        return OCRResult(
            image_id=image_id,
            image_type=image_type,
            full_text="\n".join(text_lines),
            boxes=boxes,
            total_detections=len(boxes),
            average_confidence=avg_conf,
            min_confidence=min_conf,
            max_confidence=max_conf,
            high_confidence_count=high_conf_count,
            engine_name=self.engine_name,
            processing_time_ms=elapsed_ms,
            status="COMPLETED"
        )

    @staticmethod
    def visualize_ocr_boxes(
        image_path: str,
        ocr_result: OCRResult,
        output_path: Optional[str] = None
    ) -> Optional[np.ndarray]:
        """
        Development debug representation:
        Overlays OCR polygons, bounding boxes, recognized text, and confidence scores
        onto the original image for visual inspection of statutory text regions.
        """
        if not os.path.exists(image_path):
            return None
        img = cv2.imread(image_path)
        if img is None:
            return None

        annotated = img.copy()
        for b in ocr_result.boxes:
            bbox = b.bounding_box
            pts = bbox.get("polygon")
            if pts and len(pts) >= 4:
                poly_arr = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(annotated, [poly_arr], isClosed=True, color=(0, 255, 0), thickness=2)
            else:
                cv2.rectangle(
                    annotated,
                    (bbox["x1"], bbox["y1"]),
                    (bbox["x2"], bbox["y2"]),
                    color=(0, 255, 0),
                    thickness=2
                )
            label = f"{b.text} ({b.confidence:.2f})"
            cv2.putText(
                annotated,
                label,
                (max(0, bbox["x1"]), max(15, bbox["y1"] - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 255),
                1,
                cv2.LINE_AA
            )

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            cv2.imwrite(output_path, annotated)

        return annotated
