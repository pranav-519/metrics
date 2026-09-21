import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.session import SessionLocal, engine, Base
from app.models.models import (
    ProductCategory, ComplianceRule, Scan, ScanImage,
    ExtractedDeclaration, RuleValidationResult, ComplianceState, ImageQualityStatus
)

def seed_database(db: Session = None):
    """
    Initializes database tables and populates statutory categories, versioned rules,
    and demo inspection scans with realistic compliance scenarios.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # 1. Seed Categories if empty
        if db.query(ProductCategory).count() == 0:
            categories = [
                ProductCategory(
                    code="food_grocery",
                    name="Food / Grocery",
                    description="Packaged foodstuffs, confectionery, staples, snacks, edible oils, and beverages."
                ),
                ProductCategory(
                    code="cosmetics",
                    name="Cosmetics",
                    description="Skin care, soaps, shampoos, personal care products, perfumes, and beauty preparations."
                ),
                ProductCategory(
                    code="household_products",
                    name="Household Products",
                    description="Detergents, cleaning agents, insecticides, disinfectants, and paper products."
                ),
                ProductCategory(
                    code="other_packaged",
                    name="Other Packaged Commodities",
                    description="General consumer goods, stationary, electronics accessories, and miscellaneous commodities."
                ),
            ]
            db.add_all(categories)
            db.commit()

        # 2. Seed Compliance Rules if empty
        if db.query(ComplianceRule).count() == 0:
            food_cat = db.query(ProductCategory).filter_by(code="food_grocery").first()
            rules = [
                ComplianceRule(
                    rule_id="LMR-2011-R6-MRP",
                    category_id=None, # Applicable across all categories
                    field_target="mrp",
                    requirement="Maximum Retail Price (MRP) clearly stated with the statutory clause 'inclusive of all taxes' or 'incl. of all taxes'.",
                    validation_type="format",
                    rule_reference="Rule 6(1)(e), Legal Metrology (PC) Rules 2011",
                    version="2024.1",
                    effective_from="2011-11-01",
                    is_mandatory=True,
                    is_active=True,
                    suggested_action="Ensure MRP is printed clearly with statutory tax inclusion wording."
                ),
                ComplianceRule(
                    rule_id="LMR-2011-R6-NETQTY",
                    category_id=None,
                    field_target="net_quantity",
                    requirement="Net quantity expressed in standard units of weight, measure, or number (g, kg, mL, L, N). Terms like 'when packed' are prohibited.",
                    validation_type="format",
                    rule_reference="Rule 6(1)(d) & Rule 11, Legal Metrology (PC) Rules 2011",
                    version="2024.1",
                    effective_from="2011-11-01",
                    is_mandatory=True,
                    is_active=True,
                    suggested_action="Standardize metric symbol and remove non-statutory qualifiers."
                ),
                ComplianceRule(
                    rule_id="LMR-2011-R6-USP",
                    category_id=None,
                    field_target="unit_sale_price",
                    requirement="Unit Sale Price (e.g. ₹ per g / ₹ per mL / ₹ per item) declared on commodities where package exceeds statutory thresholds.",
                    validation_type="unit_sale_price",
                    rule_reference="Rule 6(11), Legal Metrology (PC) Amendment Rules",
                    version="2024.1",
                    effective_from="2022-12-01",
                    is_mandatory=False, # Mandatory on packages above 1kg/1L
                    is_active=True,
                    suggested_action="Add Unit Sale Price declaration calculated as MRP divided by net weight."
                ),
                ComplianceRule(
                    rule_id="LMR-2011-R6-MFG",
                    category_id=None,
                    field_target="manufacturer_name",
                    requirement="Name and complete address of the manufacturer, packer, or importer with postal pin code.",
                    validation_type="presence",
                    rule_reference="Rule 6(1)(a) & (b), Legal Metrology (PC) Rules 2011",
                    version="2024.1",
                    effective_from="2011-11-01",
                    is_mandatory=True,
                    is_active=True,
                    suggested_action="Print legal entity name and complete physical address of manufacture or packaging."
                ),
                ComplianceRule(
                    rule_id="LMR-2011-R6-DATE",
                    category_id=None,
                    field_target="mfg_date",
                    requirement="Month and year in which commodity is manufactured, packed, or pre-packed.",
                    validation_type="format",
                    rule_reference="Rule 6(1)(c), Legal Metrology (PC) Rules 2011",
                    version="2024.1",
                    effective_from="2011-11-01",
                    is_mandatory=True,
                    is_active=True,
                    suggested_action="Declare manufacturing or packing date in MM/YYYY format."
                ),
                ComplianceRule(
                    rule_id="LMR-2011-R6-EXPIRY",
                    category_id=food_cat.id if food_cat else None,
                    field_target="expiry_date",
                    requirement="Best Before or Expiry Date on commodities subject to spoilage or limited shelf-life.",
                    validation_type="presence",
                    rule_reference="Rule 6(1)(c) proviso, Legal Metrology (PC) Rules 2011",
                    version="2024.1",
                    effective_from="2011-11-01",
                    is_mandatory=True,
                    is_active=True,
                    suggested_action="State Best Before duration or specific Expiry Date."
                ),
                ComplianceRule(
                    rule_id="LMR-2011-R6-CARE",
                    category_id=None,
                    field_target="consumer_care",
                    requirement="Name, address, telephone number, and email address of consumer grievance cell.",
                    validation_type="format",
                    rule_reference="Rule 6(1)(g), Legal Metrology (PC) Rules 2011",
                    version="2024.1",
                    effective_from="2011-11-01",
                    is_mandatory=True,
                    is_active=True,
                    suggested_action="Print consumer helpline phone and email on the principal or back panel."
                ),
            ]
            db.add_all(rules)
            db.commit()

        # 3. Seed Sample Demo Scans if empty
        if db.query(Scan).count() == 0:
            food_cat = db.query(ProductCategory).filter_by(code="food_grocery").first()
            household_cat = db.query(ProductCategory).filter_by(code="household_products").first()

            # Demo Scan 1: Britannia Good Day (VERIFIED_COMPLIANT)
            scan1 = Scan(
                product_name="Britannia Good Day Cashew Cookies (500g)",
                category_id=food_cat.id,
                overall_status=ComplianceState.VERIFIED_COMPLIANT,
                compliance_score=98.5,
                summary_verdict="All evaluated mandatory packaged commodity declarations are verified compliant under Legal Metrology Rules 2011.",
                is_calibrated=True,
                calibration_method="reference_id_card_width",
                pixels_per_mm=12.4,
                is_demo=True,
                analysis_step="COMPLETED",
                created_at=datetime.utcnow()
            )
            db.add(scan1)
            db.commit()

            img1 = ScanImage(
                scan_id=scan1.id,
                image_role="front",
                file_path="/demo_samples/good_day_front.jpg",
                original_filename="good_day_front.jpg",
                quality_status=ImageQualityStatus.GOOD,
                blur_score=142.0,
                glare_score=2.1,
                lighting_score=94.0,
                resolution_w=1920,
                resolution_h=1080,
                quality_notes="Optimal lighting, contrast, and text sharpness."
            )
            db.add(img1)

            decl1_list = [
                ExtractedDeclaration(
                    scan_id=scan1.id,
                    field_name="mrp",
                    display_name="Maximum Retail Price (MRP)",
                    detected_value="₹75.00 (Incl. of all taxes)",
                    normalized_value="₹75.00",
                    raw_ocr_snippet="MRP Rs. 75.00 (INCL. OF ALL TAXES)",
                    confidence=0.97,
                    status=ComplianceState.VERIFIED_COMPLIANT,
                    bounding_box={"x": 125, "y": 180, "w": 340, "h": 28},
                    source_image_role="front",
                    estimated_font_height_mm=2.8,
                    required_font_height_mm=2.0,
                    measurement_confidence="VERIFIED"
                ),
                ExtractedDeclaration(
                    scan_id=scan1.id,
                    field_name="net_quantity",
                    display_name="Net Quantity",
                    detected_value="500 g",
                    normalized_value="500 g",
                    raw_ocr_snippet="NET WEIGHT: 500 g",
                    confidence=0.96,
                    status=ComplianceState.VERIFIED_COMPLIANT,
                    bounding_box={"x": 125, "y": 140, "w": 280, "h": 26},
                    source_image_role="front",
                    estimated_font_height_mm=3.2,
                    required_font_height_mm=2.0,
                    measurement_confidence="VERIFIED"
                ),
                ExtractedDeclaration(
                    scan_id=scan1.id,
                    field_name="consumer_care",
                    display_name="Consumer Care Information",
                    detected_value="Phone: 1800-425-4449, Email: feedback@britannia.co.in",
                    normalized_value="Phone: 1800-425-4449, Email: feedback@britannia.co.in",
                    raw_ocr_snippet="FOR CONSUMER FEEDBACK: CALL 1800-425-4449, EMAIL: feedback@britannia.co.in",
                    confidence=0.93,
                    status=ComplianceState.VERIFIED_COMPLIANT,
                    bounding_box={"x": 125, "y": 385, "w": 540, "h": 28},
                    source_image_role="front",
                    estimated_font_height_mm=1.9,
                    required_font_height_mm=1.5,
                    measurement_confidence="VERIFIED"
                )
            ]
            db.add_all(decl1_list)

            # Demo Scan 2: Detergent Powder (POTENTIAL_NON_COMPLIANCE)
            scan2 = Scan(
                product_name="Surf Excel Easy Wash Powder (1kg)",
                category_id=household_cat.id,
                overall_status=ComplianceState.POTENTIAL_NON_COMPLIANCE,
                compliance_score=68.0,
                summary_verdict="1 potential compliance discrepancy identified: Net quantity contains prohibited qualifier 'When Packed'.",
                is_calibrated=False,
                calibration_method="uncalibrated_heuristic",
                pixels_per_mm=11.8,
                is_demo=True,
                analysis_step="COMPLETED",
                created_at=datetime.utcnow()
            )
            db.add(scan2)
            db.commit()

            img2 = ScanImage(
                scan_id=scan2.id,
                image_role="back",
                file_path="/demo_samples/surf_excel_back.jpg",
                original_filename="surf_excel_back.jpg",
                quality_status=ImageQualityStatus.ACCEPTABLE,
                blur_score=78.0,
                glare_score=4.8,
                lighting_score=85.0,
                resolution_w=1280,
                resolution_h=960,
                quality_notes="Moderate sharpness; consumer care corner is slightly shadowed."
            )
            db.add(img2)

            decl2_list = [
                ExtractedDeclaration(
                    scan_id=scan2.id,
                    field_name="net_quantity",
                    display_name="Net Quantity",
                    detected_value="1.0 kg (Note: 'When Packed' phrase detected)",
                    normalized_value="1.0 kg",
                    raw_ocr_snippet="NET WEIGHT: 1.0 kg (When Packed)",
                    confidence=0.84,
                    status=ComplianceState.POTENTIAL_NON_COMPLIANCE,
                    bounding_box={"x": 110, "y": 150, "w": 310, "h": 28},
                    source_image_role="back",
                    estimated_font_height_mm=3.0,
                    required_font_height_mm=2.0,
                    measurement_confidence="ESTIMATED"
                ),
                ExtractedDeclaration(
                    scan_id=scan2.id,
                    field_name="consumer_care",
                    display_name="Consumer Care Information",
                    detected_value="Possibly 'CONSUMER CARE: 1800...'",
                    normalized_value=None,
                    raw_ocr_snippet="CONSUMER CARE: 1800-10-22-221",
                    confidence=0.42,
                    status=ComplianceState.UNABLE_TO_VERIFY,
                    bounding_box={"x": 110, "y": 320, "w": 250, "h": 20},
                    source_image_role="back",
                    estimated_font_height_mm=1.6,
                    required_font_height_mm=1.5,
                    measurement_confidence="ESTIMATED"
                )
            ]
            db.add_all(decl2_list)

            # Demo Scan 3: Milk Carton (UNABLE_TO_VERIFY)
            scan3 = Scan(
                product_name="Amul Taza Homogenised Toned Milk (500ml)",
                category_id=food_cat.id,
                overall_status=ComplianceState.UNABLE_TO_VERIFY,
                compliance_score=79.0,
                summary_verdict="1 declaration panel could not be reliably verified due to image glare. Never classify as missing.",
                is_calibrated=False,
                calibration_method="uncalibrated_heuristic",
                pixels_per_mm=11.8,
                is_demo=True,
                analysis_step="COMPLETED",
                created_at=datetime.utcnow()
            )
            db.add(scan3)
            db.commit()

            img3 = ScanImage(
                scan_id=scan3.id,
                image_role="side",
                file_path="/demo_samples/amul_milk_side.jpg",
                original_filename="amul_milk_side.jpg",
                quality_status=ImageQualityStatus.POOR,
                blur_score=52.0,
                glare_score=14.5,
                lighting_score=70.0,
                resolution_w=1024,
                resolution_h=768,
                quality_notes="Significant glare on the top fold affecting expiry date legibility."
            )
            db.add(img3)

            decl3_list = [
                ExtractedDeclaration(
                    scan_id=scan3.id,
                    field_name="mrp",
                    display_name="Maximum Retail Price (MRP)",
                    detected_value="₹28.00 (Incl. of all taxes)",
                    normalized_value="₹28.00",
                    raw_ocr_snippet="MRP: Rs. 28.00 (INCL. ALL TAXES)",
                    confidence=0.94,
                    status=ComplianceState.VERIFIED_COMPLIANT,
                    bounding_box={"x": 110, "y": 170, "w": 320, "h": 26},
                    source_image_role="side",
                    estimated_font_height_mm=2.4,
                    required_font_height_mm=2.0,
                    measurement_confidence="ESTIMATED"
                ),
                ExtractedDeclaration(
                    scan_id=scan3.id,
                    field_name="expiry_date",
                    display_name="Best Before / Expiry Date",
                    detected_value="Possibly 'EXPIRY...'",
                    normalized_value=None,
                    raw_ocr_snippet="EXP... BEST BEFORE...",
                    confidence=0.38,
                    status=ComplianceState.UNABLE_TO_VERIFY,
                    bounding_box={"x": 110, "y": 245, "w": 440, "h": 24},
                    source_image_role="side",
                    estimated_font_height_mm=None,
                    required_font_height_mm=1.5,
                    measurement_confidence="UNCALIBRATED"
                )
            ]
            db.add_all(decl3_list)
            db.commit()

    finally:
        if close_db:
            db.close()

if __name__ == "__main__":
    seed_database()
    print("Database successfully seeded.")
