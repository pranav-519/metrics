from typing import List, Dict, Any, Optional
from app.models.models import ComplianceState
from app.services.ocr.base import OCRResult, OCRBoxResult
from app.services.extraction.field_extractors import ModularFieldExtractors, FieldCandidate
from app.services.extraction.normalizer import TextNormalizer

class DeclarationExtractorService:
    """
    Orchestrator for statutory Legal Metrology Packaged Commodities declarations:
    1. PRODUCT_NAME
    2. MRP
    3. NET_QUANTITY
    4. MANUFACTURER
    5. PACKER
    6. IMPORTER
    7. MANUFACTURING_DATE
    8. PACKING_DATE
    9. EXPIRY_DATE
    10. BEST_BEFORE
    11. CONSUMER_CARE
    12. COUNTRY_OF_ORIGIN

    Supports multi-image aggregation, duplicate retention, conflict detection,
    and deterministic bounding box evidence mapping.
    """

    CONFIDENCE_UNCERTAINTY_THRESHOLD = 0.55

    FIELD_ORDER = [
        "PRODUCT_NAME",
        "MRP",
        "NET_QUANTITY",
        "MANUFACTURER",
        "PACKER",
        "IMPORTER",
        "MANUFACTURING_DATE",
        "PACKING_DATE",
        "EXPIRY_DATE",
        "BEST_BEFORE",
        "CONSUMER_CARE",
        "COUNTRY_OF_ORIGIN"
    ]

    # Alias mapping for legacy compliance engine rule targets
    FIELD_ALIASES = {
        "mrp": "MRP",
        "net_quantity": "NET_QUANTITY",
        "manufacturer": "MANUFACTURER",
        "manufacturer_name": "MANUFACTURER",
        "manufacturer_address": "MANUFACTURER",
        "packer": "PACKER",
        "importer": "IMPORTER",
        "mfg_date": "MANUFACTURING_DATE",
        "manufacturing_date": "MANUFACTURING_DATE",
        "date_of_manufacture": "MANUFACTURING_DATE",
        "packing_date": "PACKING_DATE",
        "date_of_packing": "PACKING_DATE",
        "expiry_date": "EXPIRY_DATE",
        "best_before": "BEST_BEFORE",
        "consumer_care": "CONSUMER_CARE",
        "country_of_origin": "COUNTRY_OF_ORIGIN",
        "product_name": "PRODUCT_NAME"
    }

    @classmethod
    def extract_from_boxes_by_image(
        cls,
        image_boxes_map: List[Dict[str, Any]]
    ) -> List[FieldCandidate]:
        """
        Extracts structured fields across multiple images with conflict and duplicate handling.
        image_boxes_map is a list of:
        {
            "image_id": int,
            "image_role": str,
            "image_type": str,
            "boxes": List[Dict[str, Any]]
        }
        """
        all_candidates_by_field: Dict[str, List[FieldCandidate]] = {f: [] for f in cls.FIELD_ORDER}

        for img_entry in image_boxes_map:
            img_id = img_entry.get("image_id")
            img_role = (img_entry.get("image_type") or img_entry.get("image_role") or "front").lower()
            boxes = img_entry.get("boxes", [])

            # Extract 12 fields for this image
            img_candidates = cls._extract_single_image(boxes, img_id, img_role)
            for f_name, cand in img_candidates.items():
                if cand.status != "NOT_FOUND":
                    all_candidates_by_field[f_name].append(cand)

        # Aggregate across images: resolve primary vs alternates and detect conflicts
        final_fields: List[FieldCandidate] = []
        for field_name in cls.FIELD_ORDER:
            cands = all_candidates_by_field[field_name]
            if not cands:
                # Field was not found on any panel
                display_name = cls._get_display_name(field_name)
                final_fields.append(FieldCandidate(
                    field_name=field_name,
                    display_name=display_name,
                    status="NOT_FOUND",
                    value=None,
                    confidence=0.0
                ))
            elif len(cands) == 1:
                final_fields.append(cands[0])
            else:
                # Multi-image resolution
                resolved = cls._resolve_multi_image_candidates(field_name, cands)
                final_fields.append(resolved)

        return final_fields

    @classmethod
    def _extract_single_image(
        cls,
        boxes: List[Dict[str, Any]],
        image_id: Optional[int],
        image_role: str
    ) -> Dict[str, FieldCandidate]:
        """Extracts candidate values for an individual image."""
        results: Dict[str, FieldCandidate] = {}

        results["PRODUCT_NAME"] = ModularFieldExtractors.extract_product_name(boxes, image_id, image_role)
        results["MRP"] = ModularFieldExtractors.extract_mrp(boxes, image_id, image_role)
        results["NET_QUANTITY"] = ModularFieldExtractors.extract_net_quantity(boxes, image_id, image_role)

        date_results = ModularFieldExtractors.extract_dates(boxes, image_id, image_role)
        results.update(date_results)

        entity_results = ModularFieldExtractors.extract_entities(boxes, image_id, image_role)
        results.update(entity_results)

        results["CONSUMER_CARE"] = ModularFieldExtractors.extract_consumer_care(boxes, image_id, image_role)
        results["COUNTRY_OF_ORIGIN"] = ModularFieldExtractors.extract_country_of_origin(boxes, image_id, image_role)

        return results

    @classmethod
    def _resolve_multi_image_candidates(
        cls,
        field_name: str,
        candidates: List[FieldCandidate]
    ) -> FieldCandidate:
        """
        Selects primary candidate from multiple detections, preserves alternates,
        and identifies value conflicts between different images.
        """
        # Sort by confidence descending, tie-breaking on raw OCR confidence and completeness
        sorted_cands = sorted(
            candidates,
            key=lambda c: (round(c.confidence, 4), round(c.raw_ocr_confidence, 4), len(c.value or "")),
            reverse=True
        )
        primary = sorted_cands[0]
        alternates = sorted_cands[1:]

        # Conflict check: compare normalized value of primary against alternates
        has_conflict = False
        primary_norm = (primary.normalized_value or primary.value or "").strip().lower()

        alt_payloads = []
        for alt in alternates:
            alt_norm = (alt.normalized_value or alt.value or "").strip().lower()
            if primary_norm and alt_norm and primary_norm != alt_norm:
                # Value differs across images -> Conflict!
                has_conflict = True

            alt_payloads.append({
                "value": alt.value,
                "normalized_value": alt.normalized_value,
                "confidence": alt.confidence,
                "source_image_id": alt.source_image_id,
                "source_image_role": alt.source_image_role,
                "source_ocr_ids": alt.source_ocr_ids,
                "bounding_box": alt.bounding_box,
                "status": alt.status
            })

        # Update primary with alternate information
        primary.alternate_candidates = alt_payloads
        if has_conflict:
            primary.has_conflict = True
            primary.status = "AMBIGUOUS"

        return primary

    @staticmethod
    def _get_display_name(field_name: str) -> str:
        names = {
            "PRODUCT_NAME": "Product / Commodity Name",
            "MRP": "Maximum Retail Price (MRP)",
            "NET_QUANTITY": "Net Quantity",
            "MANUFACTURER": "Manufacturer Name & Address",
            "PACKER": "Packer Name & Address",
            "IMPORTER": "Importer Name & Address",
            "MANUFACTURING_DATE": "Date of Manufacture",
            "PACKING_DATE": "Date of Packaging",
            "EXPIRY_DATE": "Expiry Date",
            "BEST_BEFORE": "Best Before / Use By",
            "CONSUMER_CARE": "Consumer Care Details",
            "COUNTRY_OF_ORIGIN": "Country of Origin"
        }
        return names.get(field_name, field_name.replace("_", " ").title())

    # -------------------------------------------------------------
    # Compatibility method for existing scan pipeline / RuleEngine
    # -------------------------------------------------------------
    @classmethod
    def extract_all_declarations(
        cls,
        ocr_results: List[OCRResult],
        category_code: str = "food_grocery",
        source_image_role: str = "front"
    ) -> List[Dict[str, Any]]:
        """
        Legacy adapter maintaining full backward compatibility with Scan creation and
        ComplianceRuleEngine while providing rich structured fields.
        """
        image_boxes_map = []
        for ocr in ocr_results:
            boxes = [
                {
                    "text": b.text,
                    "confidence": b.confidence,
                    "bounding_box": b.bounding_box,
                    "line_number": b.line_number,
                    "image_id": getattr(b, "image_id", None) or getattr(ocr, "image_id", None),
                    "image_type": getattr(b, "image_type", None) or getattr(ocr, "image_type", "FRONT")
                }
                for b in ocr.boxes
            ]
            image_boxes_map.append({
                "image_id": getattr(ocr, "image_id", None),
                "image_role": getattr(ocr, "image_type", "FRONT").lower(),
                "image_type": getattr(ocr, "image_type", "FRONT"),
                "boxes": boxes
            })

        field_candidates = cls.extract_from_boxes_by_image(image_boxes_map)

        # Convert to dictionary format expected by ComplianceRuleEngine and ExtractedDeclaration persistence
        output = []
        for fc in field_candidates:
            # Map extraction status to ComplianceState for backward compatibility
            if fc.status == "FOUND":
                comp_status = ComplianceState.VERIFIED_COMPLIANT
            elif fc.status == "NOT_FOUND":
                comp_status = ComplianceState.NOT_FOUND
            elif fc.status == "LOW_CONFIDENCE":
                comp_status = ComplianceState.UNABLE_TO_VERIFY
            else: # AMBIGUOUS
                comp_status = ComplianceState.REVIEW_REQUIRED

            item = {
                "field_name": fc.field_name.lower(), # lowercase alias for compliance rule matching
                "canonical_field_name": fc.field_name,
                "display_name": fc.display_name,
                "detected_value": fc.value,
                "normalized_value": fc.normalized_value,
                "raw_value": fc.raw_value,
                "raw_ocr_snippet": fc.raw_value,
                "unit": fc.unit,
                "currency": fc.currency,
                "confidence": fc.confidence,
                "field_confidence": fc.confidence,
                "raw_ocr_confidence": fc.raw_ocr_confidence,
                "status": comp_status,
                "extraction_status": fc.status,
                "bounding_box": fc.bounding_box,
                "source_image_id": fc.source_image_id,
                "source_image_role": fc.source_image_role or "front",
                "source_ocr_ids": fc.source_ocr_ids,
                "evidence": fc.evidence,
                "extraction_method": fc.extraction_method,
                "has_conflict": fc.has_conflict,
                "alternate_candidates": fc.alternate_candidates,
            }
            output.append(item)

        return output
