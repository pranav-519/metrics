import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app
from app.services.image_processing.quality import ImageQualityService
from app.services.measurement.calibration import PhysicalMeasurementService
from app.models.models import ComplianceState

client = TestClient(app)

def create_dummy_image_bytes():
    """Generates a small in-memory valid JPEG for testing file uploads."""
    img = Image.new('RGB', (800, 600), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Legal Metrology" in data["service"]

def test_get_categories():
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4
    codes = [c["code"] for c in data]
    assert "food_grocery" in codes
    assert "household_products" in codes

def test_get_rules():
    response = client.get("/api/rules")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 7
    rule_ids = [r["rule_id"] for r in data]
    assert "LMR-2011-R6-MRP" in rule_ids
    assert "LMR-2011-R6-NETQTY" in rule_ids

def test_dashboard_stats():
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_scans"] >= 3
    assert len(data["recent_scans"]) >= 3

def test_create_and_retrieve_scan():
    img_buf = create_dummy_image_bytes()
    files = {
        "front_image": ("front_test.jpg", img_buf, "image/jpeg")
    }
    data = {
        "product_name": "Test Glucose Biscuits (500g)",
        "category_id": "1",
        "calibration_method": "reference_id_card_width",
        "pixels_per_mm": "12.4"
    }

    # Post scan
    response = client.post("/api/scans", data=data, files=files)
    assert response.status_code == 200
    scan_data = response.json()
    scan_id = scan_data["id"]
    assert scan_data["product_name"] == "Test Glucose Biscuits (500g)"
    assert scan_data["is_calibrated"] is True
    assert len(scan_data["declarations"]) > 0
    assert len(scan_data["rule_results"]) > 0

    # Retrieve scan detail
    detail_res = client.get(f"/api/scans/{scan_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == scan_id
    assert detail["overall_status"] in [
        ComplianceState.VERIFIED_COMPLIANT.value,
        ComplianceState.POTENTIAL_NON_COMPLIANCE.value,
        ComplianceState.UNABLE_TO_VERIFY.value,
        ComplianceState.REVIEW_REQUIRED.value,
    ]

def test_physical_measurement_service():
    # Test uncalibrated heuristic
    meas = PhysicalMeasurementService.estimate_font_height_mm(bbox_height_px=40, is_calibrated=False)
    assert meas["confidence"] == "ESTIMATED"
    assert meas["height_mm"] > 0

    # Test calibrated with known card
    calib = PhysicalMeasurementService.calibrate_from_reference("id_card_width", 1027.2)
    assert calib.is_calibrated is True
    assert calib.pixels_per_mm == 12.0
