import io
import os
import pytest
from PIL import Image, ImageDraw
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.ocr.engine import PretrainedOCREngine
from app.services.ocr.providers.rapidocr_provider import RapidOCREngine
from app.services.ocr.base import OCRResult, OCRBoxResult
from app.services.image_processing.quality import ImageQualityService

client = TestClient(app)

def create_image_with_text(text: str = "MRP Rs 75.00 INCL OF ALL TAXES", size=(640, 200), font_size=24) -> Image.Image:
    """Generates an in-memory synthetic image with crisp readable text."""
    img = Image.new("RGB", size, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 80), text, fill=(0, 0, 0))
    return img

def create_blank_image(size=(640, 200), color=(255, 255, 255)) -> Image.Image:
    """Generates a blank image without any text."""
    return Image.new("RGB", size, color=color)

def test_rapidocr_initialization():
    """1. Test that RapidOCR initializes correctly as primary engine."""
    provider = RapidOCREngine()
    assert provider.is_available() is True
    assert provider.engine_name == "RapidOCR-ONNX"

    orchestrator = PretrainedOCREngine(preferred_engine="rapidocr")
    assert orchestrator.engine_name == "RapidOCR-ONNX"

def test_real_image_produces_detections(tmp_path):
    """2. Real image produces OCR detections when text is visible."""
    img = create_image_with_text("NET WEIGHT 500 g")
    test_path = str(tmp_path / "test_label.jpg")
    img.save(test_path, format="JPEG")

    engine = PretrainedOCREngine()
    res = engine.extract_text(test_path)

    assert res.status == "COMPLETED"
    assert res.total_detections > 0
    assert len(res.boxes) > 0
    assert any("500" in b.text or "NET" in b.text.upper() or "WEIGHT" in b.text.upper() for b in res.boxes)

def test_ocr_output_contains_confidence(tmp_path):
    """3. OCR output contains genuine per-detection confidence scores and averages."""
    img = create_image_with_text("MAXIMUM RETAIL PRICE Rs 120.00")
    test_path = str(tmp_path / "test_mrp.jpg")
    img.save(test_path, format="JPEG")

    engine = PretrainedOCREngine()
    res = engine.extract_text(test_path)

    assert res.total_detections > 0
    assert 0.0 < res.average_confidence <= 1.0
    for box in res.boxes:
        assert isinstance(box.confidence, float)
        assert 0.0 <= box.confidence <= 1.0

def test_ocr_output_contains_bounding_boxes(tmp_path):
    """4. OCR output contains accurate pixel and normalized bounding box coordinates."""
    img = create_image_with_text("MFD DATE 15/08/2026", size=(800, 300))
    test_path = str(tmp_path / "test_bbox.jpg")
    img.save(test_path, format="JPEG")

    engine = PretrainedOCREngine()
    res = engine.extract_text(test_path)

    assert len(res.boxes) > 0
    first_box = res.boxes[0]
    bbox = first_box.bounding_box

    # Check required coordinate keys
    for key in ["x1", "y1", "x2", "y2", "x", "y", "w", "h", "x_rel", "y_rel", "w_rel", "h_rel"]:
        assert key in bbox, f"Missing key {key} in bounding_box"

    # Coordinates must be positive and within image dimensions
    assert bbox["x1"] >= 0
    assert bbox["y1"] >= 0
    assert bbox["x2"] <= 800
    assert bbox["y2"] <= 300
    assert 0.0 <= bbox["x_rel"] <= 1.0
    assert 0.0 <= bbox["y_rel"] <= 1.0
    assert bbox["w"] > 0
    assert bbox["h"] > 0

def test_empty_image_does_not_produce_fake_text(tmp_path):
    """5. Blank or empty image does NOT produce fabricated/mock text."""
    blank_img = create_blank_image(size=(600, 200))
    test_path = str(tmp_path / "blank_package.jpg")
    blank_img.save(test_path, format="JPEG")

    engine = PretrainedOCREngine()
    res = engine.extract_text(test_path)

    assert res.status == "NO_TEXT_DETECTED"
    assert res.total_detections == 0
    assert len(res.boxes) == 0
    assert res.full_text == ""
    assert res.average_confidence == 0.0

def test_low_quality_triggers_preprocessing_retry(tmp_path):
    """6. Low-contrast or noisy image triggers preprocessing and retry."""
    # Low-contrast image (gray text on slightly lighter gray)
    img = Image.new("RGB", (640, 200), color=(180, 180, 180))
    draw = ImageDraw.Draw(img)
    draw.text((40, 80), "USE BY 12/2027", fill=(140, 140, 140))

    orig_path = str(tmp_path / "low_contrast.jpg")
    prep_path = str(tmp_path / "preprocessed_low_contrast.jpg")
    img.save(orig_path, format="JPEG")

    engine = PretrainedOCREngine()
    res = engine.extract_text(
        image_path=orig_path,
        preprocessed_path=prep_path,
        retry_after_preprocess=True,
        force_preprocess=True,
        max_attempts=2
    )

    # Preprocessed file should be generated and retry attempted
    assert os.path.exists(prep_path)
    assert res.attempt_count == 2
    assert res.total_detections > 0

def test_ocr_provider_failure_is_handled_cleanly():
    """7. Provider handles missing or corrupt files without unhandled crashes."""
    engine = PretrainedOCREngine()
    res = engine.extract_text("non_existent_file_path_xyz_123.jpg")

    assert res.status == "FAILED"
    assert res.total_detections == 0
    assert len(res.boxes) == 0
    assert "not found" in res.error_message.lower()

def test_multi_image_isolation(tmp_path):
    """8. Multiple images remain associated with their respective image IDs and roles."""
    front_img = create_image_with_text("FRONT PANEL BRAND NAME")
    back_img = create_image_with_text("BACK PANEL CONSUMER CARE 1800-000-000")

    front_path = str(tmp_path / "front.jpg")
    back_path = str(tmp_path / "back.jpg")
    front_img.save(front_path, format="JPEG")
    back_img.save(back_path, format="JPEG")

    engine = PretrainedOCREngine()
    multi_results = engine.extract_multi_images([
        {"file_path": front_path, "image_id": 101, "image_type": "FRONT"},
        {"file_path": back_path, "image_id": 102, "image_type": "BACK"}
    ])

    assert len(multi_results) == 2
    front_res, back_res = multi_results[0], multi_results[1]

    assert front_res.image_id == 101
    assert front_res.image_type == "FRONT"
    assert all(b.image_id == 101 for b in front_res.boxes)

    assert back_res.image_id == 102
    assert back_res.image_type == "BACK"
    assert all(b.image_id == 102 for b in back_res.boxes)

def test_no_filename_based_ocr_behavior(tmp_path):
    """9. Verify filename has ZERO influence on OCR text (Phase 1 fake fallback removed)."""
    # In Phase 1, filenames containing 'detergent' or 'milk' returned hardcoded declarations.
    # We now verify that blank images with these filenames return NO text.
    blank_detergent = create_blank_image()
    blank_milk = create_blank_image()

    det_path = str(tmp_path / "surf_excel_detergent_pack.jpg")
    milk_path = str(tmp_path / "amul_toned_milk_carton.png")
    blank_detergent.save(det_path, format="JPEG")
    blank_milk.save(milk_path, format="PNG")

    engine = PretrainedOCREngine()
    det_res = engine.extract_text(det_path)
    milk_res = engine.extract_text(milk_path)

    assert det_res.total_detections == 0
    assert "SURF EXCEL" not in det_res.full_text
    assert milk_res.total_detections == 0
    assert "AMUL" not in milk_res.full_text

def test_api_staged_quality_and_ocr_endpoints():
    """10. API endpoints POST /api/scans/{id}/quality-check and POST /api/scans/{id}/ocr return structured data."""
    # Create scan via composite endpoint
    img = create_image_with_text("MRP Rs 99.00 INCL TAXES", size=(800, 600))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"front_image": ("package_front.jpg", buf, "image/jpeg")}
    data = {"product_name": "API Test Biscuit Pack", "category_id": "1"}

    create_res = client.post("/api/scans", data=data, files=files)
    assert create_res.status_code == 200
    scan_id = create_res.json()["id"]

    # 1. Test POST /api/scans/{scan_id}/quality-check
    qc_res = client.post(f"/api/scans/{scan_id}/quality-check")
    assert qc_res.status_code == 200
    qc_data = qc_res.json()
    assert qc_data["scan_id"] == scan_id
    assert qc_data["overall_quality_status"] in ["GOOD", "ACCEPTABLE", "POOR"]
    assert len(qc_data["images"]) >= 1
    assert "blur_score" in qc_data["images"][0]
    assert "glare_percentage" in qc_data["images"][0]

    # 2. Test POST /api/scans/{scan_id}/ocr
    ocr_api_res = client.post(f"/api/scans/{scan_id}/ocr")
    assert ocr_api_res.status_code == 200
    ocr_data = ocr_api_res.json()
    assert ocr_data["scan_id"] == scan_id
    assert ocr_data["ocr_engine"] in ["PaddleOCR-PP-OCRv6", "RapidOCR-ONNX"]
    assert len(ocr_data["results"]) >= 1
    assert ocr_data["results"][0]["status"] == "COMPLETED"
    assert ocr_data["results"][0]["total_detections"] > 0
    assert len(ocr_data["results"][0]["boxes"]) > 0
