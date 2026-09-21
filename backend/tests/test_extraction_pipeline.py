import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import get_db, SessionLocal
from app.models.models import Scan, ScanImage, OCRRecord, ExtractedDeclaration, ComplianceState, ExtractionStatus
from app.services.extraction.field_extractors import ModularFieldExtractors
from app.services.extraction.declarations import DeclarationExtractorService
from app.services.extraction.normalizer import TextNormalizer
from app.services.extraction.evidence_matcher import EvidenceMatcher

client = TestClient(app)

# =====================================================================
# 1. MRP EXTRACTION TEST
# =====================================================================
def test_mrp_extraction():
    boxes = [
        {
            "id": 1,
            "text": "M.R.P. Rs. 149.50 (Incl. of all taxes)",
            "confidence": 0.95,
            "bounding_box": {"x1": 10, "y1": 50, "x2": 300, "y2": 70, "x": 10, "y": 50, "w": 290, "h": 20},
            "line_number": 1
        }
    ]
    candidate = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
    assert candidate.status == "FOUND"
    assert candidate.field_name == "MRP"
    assert candidate.normalized_value == "149.50"
    assert candidate.currency == "INR"
    assert "₹149.50" in candidate.value
    assert "Incl. of all taxes" in candidate.value
    assert candidate.confidence >= 0.90
    assert 1 in candidate.source_ocr_ids

# =====================================================================
# 2. NET QUANTITY EXTRACTION TEST
# =====================================================================
def test_net_quantity_extraction():
    units_to_test = [
        ("Net Qty: 500 g", "500 g", "g"),
        ("Net Wt. 1.5 kg", "1.5 kg", "kg"),
        ("Net Content: 250 ml", "250 ml", "ml"),
        ("Net Volume: 2 L", "2 L", "L"),
    ]
    for raw_str, expected_norm, expected_unit in units_to_test:
        boxes = [
            {
                "id": 10,
                "text": raw_str,
                "confidence": 0.92,
                "bounding_box": {"x1": 20, "y1": 100, "x2": 220, "y2": 120, "x": 20, "y": 100, "w": 200, "h": 20},
                "line_number": 2
            }
        ]
        candidate = ModularFieldExtractors.extract_net_quantity(boxes, image_id=1, image_role="front")
        assert candidate.status == "FOUND"
        assert candidate.normalized_value == expected_norm
        assert candidate.unit == expected_unit
        assert 10 in candidate.source_ocr_ids

# =====================================================================
# 3. CONTEXTUAL DATES EXTRACTION TEST
# =====================================================================
def test_date_extraction_contextual():
    boxes = [
        {"id": 21, "text": "MFD: 15/08/2026", "confidence": 0.94, "bounding_box": {"x1": 10, "y1": 10, "x2": 150, "y2": 30, "w": 140, "h": 20}, "line_number": 1},
        {"id": 22, "text": "PKD ON: 08-2026", "confidence": 0.91, "bounding_box": {"x1": 10, "y1": 40, "x2": 150, "y2": 60, "w": 140, "h": 20}, "line_number": 2},
        {"id": 23, "text": "EXPIRY DATE: 15-08-2027", "confidence": 0.93, "bounding_box": {"x1": 10, "y1": 70, "x2": 180, "y2": 90, "w": 170, "h": 20}, "line_number": 3},
        {"id": 24, "text": "Best Before: 12 months from packing", "confidence": 0.89, "bounding_box": {"x1": 10, "y1": 100, "x2": 220, "y2": 120, "w": 210, "h": 20}, "line_number": 4},
    ]
    dates = ModularFieldExtractors.extract_dates(boxes, image_id=2, image_role="back")
    assert dates["MANUFACTURING_DATE"].status == "FOUND"
    assert dates["MANUFACTURING_DATE"].normalized_value == "15/08/2026"

    assert dates["PACKING_DATE"].status == "FOUND"
    assert dates["PACKING_DATE"].normalized_value == "08-2026"

    assert dates["EXPIRY_DATE"].status == "FOUND"
    assert dates["EXPIRY_DATE"].normalized_value == "15-08-2027"

# =====================================================================
# 4. AMBIGUOUS DATE EXTRACTION TEST (NO LABEL CONTEXT)
# =====================================================================
def test_date_extraction_ambiguous():
    boxes = [
        {"id": 25, "text": "Batch: B102", "confidence": 0.90, "bounding_box": {"x1": 10, "y1": 10, "x2": 100, "y2": 30, "w": 90, "h": 20}, "line_number": 1},
        {"id": 26, "text": "08/2026", "confidence": 0.88, "bounding_box": {"x1": 10, "y1": 40, "x2": 90, "y2": 60, "w": 80, "h": 20}, "line_number": 2},
    ]
    dates = ModularFieldExtractors.extract_dates(boxes, image_id=2, image_role="back")
    # Date exists without explicit label -> Must be marked AMBIGUOUS rather than guessing!
    assert dates["MANUFACTURING_DATE"].status == "AMBIGUOUS"
    assert dates["MANUFACTURING_DATE"].value == "08/2026"

# =====================================================================
# 5. MANUFACTURER EXTRACTION WITH MULTI-LINE ADDRESS
# =====================================================================
def test_manufacturer_extraction_multi_line():
    boxes = [
        {"id": 31, "text": "Manufactured by: Himalaya Wellness Company", "confidence": 0.92, "bounding_box": {"x1": 20, "y1": 100, "x2": 350, "y2": 120, "x": 20, "y": 100, "w": 330, "h": 20}, "line_number": 5},
        {"id": 32, "text": "Makali, Bengaluru 562162", "confidence": 0.90, "bounding_box": {"x1": 20, "y1": 125, "x2": 260, "y2": 145, "x": 20, "y": 125, "w": 240, "h": 20}, "line_number": 6},
        {"id": 33, "text": "Karnataka, India", "confidence": 0.91, "bounding_box": {"x1": 20, "y1": 150, "x2": 180, "y2": 170, "x": 20, "y": 150, "w": 160, "h": 20}, "line_number": 7},
    ]
    entities = ModularFieldExtractors.extract_entities(boxes, image_id=1, image_role="back")
    mfg = entities["MANUFACTURER"]
    assert mfg.status == "FOUND"
    assert "Himalaya Wellness" in mfg.value
    assert "Bengaluru 562162" in mfg.value
    assert "Karnataka, India" in mfg.value
    assert 31 in mfg.source_ocr_ids
    assert 32 in mfg.source_ocr_ids
    assert 33 in mfg.source_ocr_ids

# =====================================================================
# 6. PACKER EXTRACTION TEST
# =====================================================================
def test_packer_extraction():
    boxes = [
        {"id": 41, "text": "Packed by: ABC Packaging Pvt Ltd, Industrial Area, Okhla, New Delhi", "confidence": 0.93, "bounding_box": {"x1": 15, "y1": 80, "x2": 450, "y2": 100, "x": 15, "y": 80, "w": 435, "h": 20}, "line_number": 3}
    ]
    entities = ModularFieldExtractors.extract_entities(boxes, image_id=1, image_role="back")
    packer = entities["PACKER"]
    assert packer.status == "FOUND"
    assert "ABC Packaging Pvt Ltd" in packer.value
    assert 41 in packer.source_ocr_ids

# =====================================================================
# 7. IMPORTER EXTRACTION TEST
# =====================================================================
def test_importer_extraction():
    boxes = [
        {"id": 51, "text": "Imported by: Global Logistics & Trade India Ltd, Andheri East, Mumbai", "confidence": 0.94, "bounding_box": {"x1": 20, "y1": 90, "x2": 480, "y2": 110, "x": 20, "y": 90, "w": 460, "h": 20}, "line_number": 4}
    ]
    entities = ModularFieldExtractors.extract_entities(boxes, image_id=1, image_role="back")
    importer = entities["IMPORTER"]
    assert importer.status == "FOUND"
    assert "Global Logistics" in importer.value
    assert 51 in importer.source_ocr_ids

# =====================================================================
# 8. CONSUMER CARE EXTRACTION TEST (GROUPED CONTACT)
# =====================================================================
def test_consumer_care_extraction_grouped():
    boxes = [
        {"id": 61, "text": "Consumer Care Cell:", "confidence": 0.92, "bounding_box": {"x1": 30, "y1": 200, "x2": 200, "y2": 220, "x": 30, "y": 200, "w": 170, "h": 20}, "line_number": 8},
        {"id": 62, "text": "Toll Free: 1800-200-1234", "confidence": 0.94, "bounding_box": {"x1": 30, "y1": 225, "x2": 220, "y2": 245, "x": 30, "y": 225, "w": 190, "h": 20}, "line_number": 9},
        {"id": 63, "text": "Email: care@company.com", "confidence": 0.95, "bounding_box": {"x1": 30, "y1": 250, "x2": 230, "y2": 270, "x": 30, "y": 250, "w": 200, "h": 20}, "line_number": 10},
    ]
    cand = ModularFieldExtractors.extract_consumer_care(boxes, image_id=1, image_role="back")
    assert cand.status == "FOUND"
    assert "1800-200-1234" in cand.value
    assert "care@company.com" in cand.value
    assert 61 in cand.source_ocr_ids
    assert 62 in cand.source_ocr_ids
    assert 63 in cand.source_ocr_ids

# =====================================================================
# 9. COUNTRY OF ORIGIN EXTRACTION TEST
# =====================================================================
def test_country_of_origin_extraction():
    boxes = [
        {"id": 71, "text": "Country of Origin: India", "confidence": 0.96, "bounding_box": {"x1": 15, "y1": 300, "x2": 220, "y2": 320, "x": 15, "y": 300, "w": 205, "h": 20}, "line_number": 12}
    ]
    cand = ModularFieldExtractors.extract_country_of_origin(boxes, image_id=1, image_role="back")
    assert cand.status == "FOUND"
    assert cand.normalized_value == "India"
    assert 71 in cand.source_ocr_ids

# =====================================================================
# 10. PRODUCT NAME EXTRACTION (LABELED VS PROMINENT TOP TEXT)
# =====================================================================
def test_product_name_extraction():
    # Explicit label
    boxes_labeled = [
        {"id": 81, "text": "Product Name: Organic Green Tea", "confidence": 0.95, "bounding_box": {"x1": 50, "y1": 40, "x2": 350, "y2": 70, "x": 50, "y": 40, "w": 300, "h": 30}, "line_number": 1}
    ]
    cand1 = ModularFieldExtractors.extract_product_name(boxes_labeled, image_id=1, image_role="front")
    assert cand1.status == "FOUND"
    assert cand1.value == "Organic Green Tea"

    # Prominent front header heuristic
    boxes_prominent = [
        {"id": 82, "text": "ALMOND BREEZE MILK", "confidence": 0.93, "bounding_box": {"x1": 50, "y1": 30, "x2": 400, "y2": 90, "x": 50, "y": 30, "w": 350, "h": 60}, "line_number": 1},
        {"id": 83, "text": "Net Qty: 1 L", "confidence": 0.90, "bounding_box": {"x1": 50, "y1": 120, "x2": 200, "y2": 140, "x": 50, "y": 120, "w": 150, "h": 20}, "line_number": 2},
    ]
    cand2 = ModularFieldExtractors.extract_product_name(boxes_prominent, image_id=1, image_role="front")
    assert cand2.status == "FOUND"
    assert cand2.value == "ALMOND BREEZE MILK"

# =====================================================================
# 11. BOUNDING BOX EVIDENCE MAPPING TEST
# =====================================================================
def test_bounding_box_evidence_mapping():
    boxes = [
        {"id": 101, "text": "MRP: ₹250.00", "confidence": 0.95, "bounding_box": {"x1": 100, "y1": 200, "x2": 280, "y2": 230, "x": 100, "y": 200, "w": 180, "h": 30}, "line_number": 5}
    ]
    cand = ModularFieldExtractors.extract_mrp(boxes, image_id=42, image_role="front")
    assert cand.source_image_id == 42
    assert cand.source_ocr_ids == [101]
    assert "enclosing_box" in cand.evidence
    assert cand.evidence["enclosing_box"]["x"] == 100
    assert cand.evidence["enclosing_box"]["y"] == 200
    assert len(cand.evidence["bounding_boxes"]) == 1

# =====================================================================
# 12. MULTIPLE OCR BOXES FORMING ONE FIELD (SPATIAL MERGE)
# =====================================================================
def test_multiple_ocr_boxes_forming_one_field():
    # Box 1: "Net Qty:" label, Box 2: "500 g" value adjacent to the right
    boxes = [
        {"id": 201, "text": "Net Qty:", "confidence": 0.94, "bounding_box": {"x1": 50, "y1": 100, "x2": 130, "y2": 120, "x": 50, "y": 100, "w": 80, "h": 20}, "line_number": 2},
        {"id": 202, "text": "500 g", "confidence": 0.92, "bounding_box": {"x1": 140, "y1": 100, "x2": 210, "y2": 120, "x": 140, "y": 100, "w": 70, "h": 20}, "line_number": 2},
    ]
    cand = ModularFieldExtractors.extract_net_quantity(boxes, image_id=5, image_role="front")
    assert cand.status == "FOUND"
    assert cand.normalized_value == "500 g"
    assert cand.extraction_method == "SPATIAL_PROXIMITY_MERGE"
    assert 201 in cand.source_ocr_ids
    assert 202 in cand.source_ocr_ids
    assert len(cand.evidence["bounding_boxes"]) == 2

# =====================================================================
# 13. MULTI-IMAGE DUPLICATE FIELD TEST (SAME VALUE, PRESERVES ALTERNATE)
# =====================================================================
def test_multi_image_duplicate_field():
    image_boxes_map = [
        {
            "image_id": 1,
            "image_role": "front",
            "boxes": [
                {"id": 301, "text": "MRP ₹120.00", "confidence": 0.88, "bounding_box": {"x1": 10, "y1": 10, "x2": 150, "y2": 30, "w": 140, "h": 20}, "line_number": 1}
            ]
        },
        {
            "image_id": 2,
            "image_role": "close_up",
            "boxes": [
                {"id": 302, "text": "MRP: ₹120.00 (Incl. of all taxes)", "confidence": 0.96, "bounding_box": {"x1": 10, "y1": 10, "x2": 320, "y2": 35, "w": 310, "h": 25}, "line_number": 1}
            ]
        }
    ]
    fields = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)
    mrp_field = next(f for f in fields if f.field_name == "MRP")
    assert mrp_field.status == "FOUND"
    assert mrp_field.normalized_value == "120.00"
    # Highest confidence (close_up image 2) should be selected as primary
    assert mrp_field.source_image_id == 2
    assert mrp_field.has_conflict is False
    assert len(mrp_field.alternate_candidates) == 1
    assert mrp_field.alternate_candidates[0]["source_image_id"] == 1

# =====================================================================
# 14. CONFLICTING FIELD VALUES ACROSS IMAGES
# =====================================================================
def test_conflicting_field_values():
    image_boxes_map = [
        {
            "image_id": 1,
            "image_role": "front",
            "boxes": [
                {"id": 401, "text": "MRP ₹120.00", "confidence": 0.90, "bounding_box": {"x1": 10, "y1": 10, "x2": 150, "y2": 30, "w": 140, "h": 20}, "line_number": 1}
            ]
        },
        {
            "image_id": 2,
            "image_role": "close_up",
            "boxes": [
                {"id": 402, "text": "MRP ₹125.00", "confidence": 0.94, "bounding_box": {"x1": 10, "y1": 10, "x2": 150, "y2": 30, "w": 140, "h": 20}, "line_number": 1}
            ]
        }
    ]
    fields = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)
    mrp_field = next(f for f in fields if f.field_name == "MRP")
    # Conflicting values -> has_conflict True and status AMBIGUOUS
    assert mrp_field.has_conflict is True
    assert mrp_field.status == "AMBIGUOUS"
    assert len(mrp_field.alternate_candidates) == 1

# =====================================================================
# 15. LOW OCR CONFIDENCE BEHAVIOR
# =====================================================================
def test_low_ocr_confidence_status():
    boxes = [
        {"id": 501, "text": "MRP ₹99.00", "confidence": 0.35, "bounding_box": {"x1": 10, "y1": 10, "x2": 120, "y2": 30, "w": 110, "h": 20}, "line_number": 1}
    ]
    cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
    assert cand.status == "LOW_CONFIDENCE"
    assert cand.raw_ocr_confidence == 0.35

# =====================================================================
# 16. NOT_FOUND BEHAVIOR
# =====================================================================
def test_not_found_behavior():
    boxes = [
        {"id": 601, "text": "Some random text with no declarations", "confidence": 0.90, "bounding_box": {"x1": 10, "y1": 10, "x2": 250, "y2": 30, "w": 240, "h": 20}, "line_number": 1}
    ]
    cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
    assert cand.status == "NOT_FOUND"
    assert cand.value is None
    assert cand.confidence == 0.0

# =====================================================================
# 17. NO FABRICATED VALUES TEST
# =====================================================================
def test_no_fabricated_values():
    # An empty image must produce strictly NOT_FOUND for all 12 fields without inventing values
    image_boxes_map = [
        {"image_id": 1, "image_role": "front", "boxes": []}
    ]
    fields = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)
    assert len(fields) == 12
    for f in fields:
        assert f.status == "NOT_FOUND"
        assert f.value is None
        assert f.confidence == 0.0
        assert f.source_ocr_ids == []

# =====================================================================
# 18. STAGED EXTRACTION API ENDPOINT TEST
# =====================================================================
def test_extract_api_endpoint():
    db = SessionLocal()
    try:
        # Create test scan and scan image
        scan = Scan(
            product_name="API Staged Test Product",
            category_id=1,
            overall_status=ComplianceState.UNABLE_TO_VERIFY,
            compliance_score=0.0
        )
        db.add(scan)
        db.commit()

        img = ScanImage(
            scan_id=scan.id,
            image_role="front",
            image_type="FRONT",
            file_path="/uploads/test_stage_front.jpg",
            quality_status="GOOD"
        )
        db.add(img)
        db.commit()

        # Add persisted OCRRecords
        rec1 = OCRRecord(
            image_id=img.id,
            scan_id=scan.id,
            text="MRP ₹199.00 (Incl. of all taxes)",
            confidence=0.96,
            bounding_box={"x": 50, "y": 100, "w": 250, "h": 30, "x1": 50, "y1": 100, "x2": 300, "y2": 130},
            line_number=1
        )
        rec2 = OCRRecord(
            image_id=img.id,
            scan_id=scan.id,
            text="Net Qty: 750 g",
            confidence=0.94,
            bounding_box={"x": 50, "y": 140, "w": 180, "h": 25, "x1": 50, "y1": 140, "x2": 230, "y2": 165},
            line_number=2
        )
        rec3 = OCRRecord(
            image_id=img.id,
            scan_id=scan.id,
            text="Country of Origin: India",
            confidence=0.95,
            bounding_box={"x": 50, "y": 180, "w": 200, "h": 25, "x1": 50, "y1": 180, "x2": 250, "y2": 205},
            line_number=3
        )
        db.add_all([rec1, rec2, rec3])
        db.commit()

        # Call POST /api/scans/{scan_id}/extract
        resp = client.post(f"/api/scans/{scan.id}/extract")
        assert resp.status_code == 200
        data = resp.json()

        assert data["scan_id"] == scan.id
        assert data["total_fields"] == 12

        field_map = {f["field_name"]: f for f in data["fields"]}
        assert "MRP" in field_map
        assert field_map["MRP"]["status"] == "FOUND"
        assert field_map["MRP"]["normalized_value"] == "199.00"
        assert field_map["MRP"]["currency"] == "INR"

        assert "NET_QUANTITY" in field_map
        assert field_map["NET_QUANTITY"]["status"] == "FOUND"
        assert field_map["NET_QUANTITY"]["unit"] == "g"

        assert "COUNTRY_OF_ORIGIN" in field_map
        assert field_map["COUNTRY_OF_ORIGIN"]["status"] == "FOUND"
        assert field_map["COUNTRY_OF_ORIGIN"]["normalized_value"] == "India"

        # Verify persistence in ExtractedDeclaration table
        persisted = db.query(ExtractedDeclaration).filter(ExtractedDeclaration.scan_id == scan.id).all()
        assert len(persisted) == 12
        persisted_mrp = next(p for p in persisted if p.field_name == "MRP")
        assert persisted_mrp.normalized_value == "199.00"
        assert persisted_mrp.currency == "INR"
        assert rec1.id in persisted_mrp.source_ocr_ids

    finally:
        # Cleanup
        db.query(ExtractedDeclaration).filter(ExtractedDeclaration.scan_id == scan.id).delete()
        db.query(OCRRecord).filter(OCRRecord.scan_id == scan.id).delete()
        db.query(ScanImage).filter(ScanImage.scan_id == scan.id).delete()
        db.query(Scan).filter(Scan.id == scan.id).delete()
        db.commit()
        db.close()
