import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from app.services.extraction.normalizer import TextNormalizer
from app.services.extraction.evidence_matcher import EvidenceMatcher

@dataclass
class FieldCandidate:
    field_name: str
    display_name: str
    value: Optional[str] = None
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    currency: Optional[str] = None
    unit: Optional[str] = None
    confidence: float = 0.0
    raw_ocr_confidence: float = 0.0
    status: str = "NOT_FOUND"  # FOUND, NOT_FOUND, AMBIGUOUS, LOW_CONFIDENCE
    source_image_id: Optional[int] = None
    source_image_role: Optional[str] = "front"
    source_ocr_ids: List[int] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    bounding_box: Optional[Dict[str, Any]] = None
    extraction_method: str = "DETERMINISTIC_CONTEXT"
    has_conflict: bool = False
    alternate_candidates: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "display_name": self.display_name,
            "value": self.value,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "currency": self.currency,
            "unit": self.unit,
            "confidence": self.confidence,
            "raw_ocr_confidence": self.raw_ocr_confidence,
            "status": self.status,
            "source_image_id": self.source_image_id,
            "source_image_role": self.source_image_role,
            "source_ocr_ids": self.source_ocr_ids,
            "evidence": self.evidence,
            "bounding_box": self.bounding_box,
            "extraction_method": self.extraction_method,
            "has_conflict": self.has_conflict,
            "alternate_candidates": self.alternate_candidates,
        }


class ModularFieldExtractors:
    """
    Modular deterministic extractors for the 12 statutory package declaration fields.
    Each extractor locates evidence boxes, parses values, and calculates explainable confidence.
    """

    DATE_PATTERN = r'(?:\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.-]+\d{2,4}\b|\b\d{1,2}[\s,.-]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.-]+\d{2,4}\b)'

    # -------------------------------------------------------------
    # 1. MRP EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_mrp(cls, boxes: List[Dict[str, Any]], image_id: Optional[int] = None, image_role: str = "front") -> FieldCandidate:
        field_name = "MRP"
        display_name = "Maximum Retail Price (MRP)"

        # Search for explicit MRP indicator or price
        mrp_regex = re.compile(r'(?:MRP|M\.?R\.?P\.?|MAX(?:IMUM)?\s+RETAIL\s+PRICE)[\s.:₹Rs/-]*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE)
        tax_regex = re.compile(r'(?:incl|inclusive)\.?\s*(?:of)?\s*(?:all)?\s*taxes', re.IGNORECASE)

        # 1. First search within single box
        for box in boxes:
            text = box.get("text", "")
            match = mrp_regex.search(text)
            if match:
                raw_amt = match.group(1).replace(",", "")
                tax_match = tax_regex.search(text)
                tax_text = " (Incl. of all taxes)" if tax_match else ""
                val_formatted = f"{float(raw_amt):.2f}"
                currency = "INR"
                raw_ocr_conf = float(box.get("confidence", 0.0))

                # Look for adjacent tax box if not in same box
                matched_boxes = [box]
                if not tax_match:
                    adj = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=200, max_y_gap=40)
                    for ab in adj:
                        if tax_regex.search(ab.get("text", "")):
                            matched_boxes.append(ab)
                            tax_text = " (Incl. of all taxes)"
                            break

                evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True, supporting_tokens_count=len(matched_boxes))

                return FieldCandidate(
                    field_name=field_name,
                    display_name=display_name,
                    value=f"₹{val_formatted}{tax_text}",
                    raw_value=box.get("text"),
                    normalized_value=val_formatted,
                    currency=currency,
                    confidence=conf,
                    raw_ocr_confidence=raw_ocr_conf,
                    status=status,
                    source_image_id=image_id,
                    source_image_role=image_role,
                    source_ocr_ids=evidence["source_ocr_ids"],
                    evidence=evidence,
                    bounding_box=evidence["enclosing_box"],
                    extraction_method="REGEX_LABEL_VALUE"
                )

        # 2. Multi-box search: Anchor box with 'MRP' or 'M.R.P' followed by value in adjacent box
        mrp_anchor_regex = re.compile(r'\b(?:MRP|M\.?R\.?P\.?|MAX(?:IMUM)?\s+RETAIL\s+PRICE)\b', re.IGNORECASE)
        val_alone_regex = re.compile(r'(?:₹|Rs\.?|RS)?\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE)

        for box in boxes:
            text = box.get("text", "")
            if mrp_anchor_regex.search(text):
                adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=250, max_y_gap=60)
                for cand_box in adj_boxes:
                    c_text = cand_box.get("text", "")
                    c_match = val_alone_regex.search(c_text)
                    if c_match and c_match.group(1):
                        num_str = c_match.group(1).replace(",", "")
                        try:
                            num_val = float(num_str)
                            if num_val > 0:
                                matched_boxes = [box, cand_box]
                                raw_ocr_conf = (float(box.get("confidence", 0.0)) + float(cand_box.get("confidence", 0.0))) / 2.0
                                val_formatted = f"{num_val:.2f}"
                                evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                                status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                                conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True, supporting_tokens_count=2)

                                return FieldCandidate(
                                    field_name=field_name,
                                    display_name=display_name,
                                    value=f"₹{val_formatted}",
                                    raw_value=f"{box.get('text')} {cand_box.get('text')}",
                                    normalized_value=val_formatted,
                                    currency="INR",
                                    confidence=conf,
                                    raw_ocr_confidence=raw_ocr_conf,
                                    status=status,
                                    source_image_id=image_id,
                                    source_image_role=image_role,
                                    source_ocr_ids=evidence["source_ocr_ids"],
                                    evidence=evidence,
                                    bounding_box=evidence["enclosing_box"],
                                    extraction_method="SPATIAL_PROXIMITY_MERGE"
                                )
                        except ValueError:
                            continue

        return FieldCandidate(field_name=field_name, display_name=display_name, status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role)

    # -------------------------------------------------------------
    # 2. NET QUANTITY EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_net_quantity(cls, boxes: List[Dict[str, Any]], image_id: Optional[int] = None, image_role: str = "front") -> FieldCandidate:
        field_name = "NET_QUANTITY"
        display_name = "Net Quantity"

        qty_units = r'(?:kg|kgs|kilogram|kilograms|g|gm|gms|gram|grams|mg|ml|m\.l\.|millilitre|l|ltr|litre|litres|cm|m|mm|units?|pcs?|n)'
        label_only_regex = re.compile(r'\b(?:NET\s*(?:QTY|QUANTITY|WT\.?|WEIGHT|VOL\.?|VOLUME|CONTENTS?)|N\.?\s*W\.?)\b', re.IGNORECASE)
        val_unit_regex = re.compile(rf'(\d+(?:\.\d+)?)\s*({qty_units})\b', re.IGNORECASE)
        combined_regex = re.compile(
            rf'\b(?:NET\s*(?:QTY|QUANTITY|WT\.?|WEIGHT|VOL\.?|VOLUME|CONTENTS?)|N\.?\s*W\.?)\s*[:.-]?\s*(\d+(?:\.\d+)?)\s*({qty_units})\b',
            re.IGNORECASE
        )

        # 1. Look for combined label + quantity in a single box
        for box in boxes:
            text = box.get("text", "")
            match = combined_regex.search(text)
            if match:
                num_str, raw_unit = match.group(1), match.group(2)
                canonical_unit = TextNormalizer.canonicalize_unit(raw_unit)
                val_formatted = f"{num_str} {canonical_unit}"
                raw_ocr_conf = float(box.get("confidence", 0.0))
                evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True)

                return FieldCandidate(
                    field_name=field_name,
                    display_name=display_name,
                    value=val_formatted,
                    raw_value=box.get("text"),
                    normalized_value=val_formatted,
                    unit=canonical_unit,
                    confidence=conf,
                    raw_ocr_confidence=raw_ocr_conf,
                    status=status,
                    source_image_id=image_id,
                    source_image_role=image_role,
                    source_ocr_ids=evidence["source_ocr_ids"],
                    evidence=evidence,
                    bounding_box=evidence["enclosing_box"],
                    extraction_method="REGEX_LABEL_VALUE"
                )

        # 2. Multi-box: Label in one box, value in adjacent box
        for box in boxes:
            text = box.get("text", "")
            if label_only_regex.search(text):
                adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=200, max_y_gap=50)
                for cand_box in adj_boxes:
                    c_text = cand_box.get("text", "")
                    c_match = val_unit_regex.search(c_text)
                    if c_match:
                        num_str, raw_unit = c_match.group(1), c_match.group(2)
                        canonical_unit = TextNormalizer.canonicalize_unit(raw_unit)
                        val_formatted = f"{num_str} {canonical_unit}"
                        matched_boxes = [box, cand_box]
                        raw_ocr_conf = (float(box.get("confidence", 0.0)) + float(cand_box.get("confidence", 0.0))) / 2.0
                        evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                        status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                        conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True, supporting_tokens_count=2)

                        return FieldCandidate(
                            field_name=field_name,
                            display_name=display_name,
                            value=val_formatted,
                            raw_value=f"{box.get('text')} {cand_box.get('text')}",
                            normalized_value=val_formatted,
                            unit=canonical_unit,
                            confidence=conf,
                            raw_ocr_confidence=raw_ocr_conf,
                            status=status,
                            source_image_id=image_id,
                            source_image_role=image_role,
                            source_ocr_ids=evidence["source_ocr_ids"],
                            evidence=evidence,
                            bounding_box=evidence["enclosing_box"],
                            extraction_method="SPATIAL_PROXIMITY_MERGE"
                        )

        # 3. Fallback: bare quantity in single box when no label exists
        nutritional_distractor_regex = re.compile(
            r'\b(?:carb(?:ohydrate)?s?|protein|fat|sugar|serving|energy|cholesterol|sodium|nutrient|nutrition|per\s+\d+)\b',
            re.IGNORECASE
        )
        for box in boxes:
            text = box.get("text", "")
            if nutritional_distractor_regex.search(text):
                continue
            match = val_unit_regex.search(text)
            if match:
                num_str, raw_unit = match.group(1), match.group(2)
                canonical_unit = TextNormalizer.canonicalize_unit(raw_unit)
                val_formatted = f"{num_str} {canonical_unit}"
                raw_ocr_conf = float(box.get("confidence", 0.0))
                evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=False, is_canonical_format=True)

                return FieldCandidate(
                    field_name=field_name,
                    display_name=display_name,
                    value=val_formatted,
                    raw_value=box.get("text"),
                    normalized_value=val_formatted,
                    unit=canonical_unit,
                    confidence=conf,
                    raw_ocr_confidence=raw_ocr_conf,
                    status=status,
                    source_image_id=image_id,
                    source_image_role=image_role,
                    source_ocr_ids=evidence["source_ocr_ids"],
                    evidence=evidence,
                    bounding_box=evidence["enclosing_box"],
                    extraction_method="REGEX_UNIT_PATTERN"
                )

        return FieldCandidate(field_name=field_name, display_name=display_name, status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role)

    # -------------------------------------------------------------
    # 3-6. DATES EXTRACTION (MANUFACTURING, PACKING, EXPIRY, BEST_BEFORE)
    # -------------------------------------------------------------
    @classmethod
    def extract_dates(cls, boxes: List[Dict[str, Any]], image_id: Optional[int] = None, image_role: str = "front") -> Dict[str, FieldCandidate]:
        results = {
            "MANUFACTURING_DATE": FieldCandidate(field_name="MANUFACTURING_DATE", display_name="Date of Manufacture", status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role),
            "PACKING_DATE": FieldCandidate(field_name="PACKING_DATE", display_name="Date of Packaging", status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role),
            "EXPIRY_DATE": FieldCandidate(field_name="EXPIRY_DATE", display_name="Expiry Date", status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role),
            "BEST_BEFORE": FieldCandidate(field_name="BEST_BEFORE", display_name="Best Before / Use By", status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role),
        }

        date_regex = re.compile(cls.DATE_PATTERN, re.IGNORECASE)

        # Contextual label patterns
        label_configs = [
            ("MANUFACTURING_DATE", re.compile(r'\b(?:MFD|MFG|DATE\s+OF\s+MFG|MANUFACTURED\s+ON|MFG\.?\s*DATE)\b', re.IGNORECASE)),
            ("PACKING_DATE", re.compile(r'\b(?:PKD|PKG|DATE\s+OF\s+P(?:AC)?K(?:IN)?G|PACKED\s+ON|PKD\.?\s*DATE)\b', re.IGNORECASE)),
            ("EXPIRY_DATE", re.compile(r'\b(?:EXP|EXPIRY|DATE\s+OF\s+EXPIRY|EXP\.?\s*DATE|USE\s+BEFORE)\b', re.IGNORECASE)),
            ("BEST_BEFORE", re.compile(r'\b(?:BEST\s+BEFORE|BB)\b', re.IGNORECASE)),
        ]

        # Scan for explicit contextual dates
        matched_box_indices = set()
        duration_regex = re.compile(r'\b(\d+\s*(?:months?|days?|years?)(?:\s+from\s+[\w\s]+)?)\b', re.IGNORECASE)

        for target_field, label_re in label_configs:
            for idx, box in enumerate(boxes):
                text = box.get("text", "")
                if label_re.search(text):
                    # 1. Date or duration in same box
                    d_match = date_regex.search(text)
                    if not d_match and target_field == "BEST_BEFORE":
                        d_match = duration_regex.search(text)
                    if d_match:
                        date_val = d_match.group(0)
                        raw_ocr_conf = float(box.get("confidence", 0.0))
                        evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                        status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                        conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True)
                        results[target_field] = FieldCandidate(
                            field_name=target_field,
                            display_name=results[target_field].display_name,
                            value=date_val,
                            raw_value=text,
                            normalized_value=date_val,
                            confidence=conf,
                            raw_ocr_confidence=raw_ocr_conf,
                            status=status,
                            source_image_id=image_id,
                            source_image_role=image_role,
                            source_ocr_ids=evidence["source_ocr_ids"],
                            evidence=evidence,
                            bounding_box=evidence["enclosing_box"],
                            extraction_method="REGEX_LABEL_VALUE"
                        )
                        matched_box_indices.add(idx)
                        break

                    # 2. Date in adjacent box
                    adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=200, max_y_gap=40)
                    found_adj = False
                    for ab in adj_boxes:
                        ab_text = ab.get("text", "")
                        ad_match = date_regex.search(ab_text)
                        if not ad_match and target_field == "BEST_BEFORE":
                            ad_match = duration_regex.search(ab_text)
                        if ad_match:
                            date_val = ad_match.group(0)
                            matched_boxes = [box, ab]
                            raw_ocr_conf = (float(box.get("confidence", 0.0)) + float(ab.get("confidence", 0.0))) / 2.0
                            evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                            status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                            conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True, supporting_tokens_count=2)
                            results[target_field] = FieldCandidate(
                                field_name=target_field,
                                display_name=results[target_field].display_name,
                                value=date_val,
                                raw_value=f"{text} {ab_text}",
                                normalized_value=date_val,
                                confidence=conf,
                                raw_ocr_confidence=raw_ocr_conf,
                                status=status,
                                source_image_id=image_id,
                                source_image_role=image_role,
                                source_ocr_ids=evidence["source_ocr_ids"],
                                evidence=evidence,
                                bounding_box=evidence["enclosing_box"],
                                extraction_method="SPATIAL_PROXIMITY_MERGE"
                            )
                            matched_box_indices.add(idx)
                            found_adj = True
                            break
                    if found_adj:
                        break

        # Check for unassigned/ambiguous dates:
        # If there's a date in the image that has NO label context and no date field found yet,
        # do NOT guess! Mark as AMBIGUOUS.
        unmatched_dates = []
        for idx, box in enumerate(boxes):
            if idx in matched_box_indices:
                continue
            text = box.get("text", "")
            # Don't consider if it matched any label
            if any(label_re.search(text) for _, label_re in label_configs):
                continue
            d_match = date_regex.search(text)
            if d_match:
                unmatched_dates.append((box, d_match.group(0)))

        # If all date fields are NOT_FOUND and an ambiguous date is present:
        if unmatched_dates and all(f.status == "NOT_FOUND" for f in results.values()):
            box, date_val = unmatched_dates[0]
            raw_ocr_conf = float(box.get("confidence", 0.0))
            evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
            conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, is_ambiguous=True)
            # Record ambiguous date on MANUFACTURING_DATE with explicit status AMBIGUOUS
            results["MANUFACTURING_DATE"] = FieldCandidate(
                field_name="MANUFACTURING_DATE",
                display_name="Date of Manufacture",
                value=date_val,
                raw_value=box.get("text"),
                normalized_value=date_val,
                confidence=conf,
                raw_ocr_confidence=raw_ocr_conf,
                status="AMBIGUOUS",
                source_image_id=image_id,
                source_image_role=image_role,
                source_ocr_ids=evidence["source_ocr_ids"],
                evidence=evidence,
                bounding_box=evidence["enclosing_box"],
                extraction_method="UNLABELLED_DATE_AMBIGUOUS"
            )

        return results

    # -------------------------------------------------------------
    # 7-9. ENTITY EXTRACTION (MANUFACTURER, PACKER, IMPORTER)
    # -------------------------------------------------------------
    @classmethod
    def extract_entities(cls, boxes: List[Dict[str, Any]], image_id: Optional[int] = None, image_role: str = "front") -> Dict[str, FieldCandidate]:
        results = {
            "MANUFACTURER": FieldCandidate(field_name="MANUFACTURER", display_name="Manufacturer Name & Address", status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role),
            "PACKER": FieldCandidate(field_name="PACKER", display_name="Packer Name & Address", status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role),
            "IMPORTER": FieldCandidate(field_name="IMPORTER", display_name="Importer Name & Address", status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role),
        }

        entity_configs = [
            ("MANUFACTURER", re.compile(r'\b(?:MANUFACTURED\s+&\s+MARKETED\s+BY|MANUFACTURED\s+(?:BY|AT)|MFD\.?\s+BY|MFG\.?\s+BY)\b', re.IGNORECASE)),
            ("PACKER", re.compile(r'\b(?:PACKED\s+(?:BY|AT)|PKD\.?\s+BY)\b', re.IGNORECASE)),
            ("IMPORTER", re.compile(r'\b(?:IMPORTED\s+(?:&\s+MARKETED\s+)?BY|IMPORTER\s*:?)\b', re.IGNORECASE)),
        ]

        for target_field, label_re in entity_configs:
            for box in boxes:
                text = box.get("text", "")
                if label_re.search(text):
                    # Multi-line address accumulation
                    matched_boxes = [box]
                    label_sub = label_re.sub("", text).strip().lstrip(":").strip()
                    accumulated_text = [label_sub] if label_sub else []

                    # Find vertically adjacent lines (multi-line address)
                    adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=300, max_y_gap=90)
                    for ab in adj_boxes:
                        ab_text = ab.get("text", "").strip()
                        # Stop if another major statutory label starts
                        if any(re.search(pat, ab_text, re.IGNORECASE) for pat in [r'\bMRP\b', r'\bNET\s+QTY\b', r'\bPKD\b', r'\bEXP\b', r'\bCONSUMER\s+CARE\b']):
                            break
                        accumulated_text.append(ab_text)
                        matched_boxes.append(ab)
                        if len(accumulated_text) >= 4:
                            break

                    combined_address = " ".join([t for t in accumulated_text if t]).strip()
                    if not combined_address and label_sub:
                        combined_address = label_sub
                    if not combined_address:
                        combined_address = text.strip()

                    raw_ocr_conf = sum(float(b.get("confidence", 0.0)) for b in matched_boxes) / max(len(matched_boxes), 1)
                    evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                    status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                    conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, supporting_tokens_count=len(matched_boxes))

                    results[target_field] = FieldCandidate(
                        field_name=target_field,
                        display_name=results[target_field].display_name,
                        value=combined_address,
                        raw_value=" \n ".join([b.get("text", "") for b in matched_boxes]),
                        normalized_value=combined_address,
                        confidence=conf,
                        raw_ocr_confidence=round(raw_ocr_conf, 4),
                        status=status,
                        source_image_id=image_id,
                        source_image_role=image_role,
                        source_ocr_ids=evidence["source_ocr_ids"],
                        evidence=evidence,
                        bounding_box=evidence["enclosing_box"],
                        extraction_method="MULTI_LINE_ADDRESS_EXPANSION"
                    )
                    break

        return results

    # -------------------------------------------------------------
    # 10. CONSUMER CARE EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_consumer_care(cls, boxes: List[Dict[str, Any]], image_id: Optional[int] = None, image_role: str = "front") -> FieldCandidate:
        field_name = "CONSUMER_CARE"
        display_name = "Consumer Care Details"

        label_re = re.compile(r'\b(?:CONSUMER\s+(?:CARE|CELL|HELPLINE)|CUSTOMER\s+(?:CARE|SUPPORT|SERVICE)|TOLL\s*FREE|HELP\s*LINE)\b', re.IGNORECASE)
        phone_re = re.compile(r'(?:(?:1800|1860)[\s-]?\d{3}[\s-]?\d{3,4}|\b(?:0\d{2,4}[-\s]?)?\d{6,10}\b)')
        email_re = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

        matched_boxes = []
        extracted_parts = []

        # Find consumer care anchor
        anchor_box = None
        for box in boxes:
            text = box.get("text", "")
            if label_re.search(text):
                anchor_box = box
                matched_boxes.append(box)
                extracted_parts.append(text.strip())
                break

        # If anchor box exists, aggregate adjacent contact info
        if anchor_box:
            adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(anchor_box, boxes, max_x_gap=300, max_y_gap=100)
            for ab in adj_boxes:
                ab_text = ab.get("text", "").strip()
                if phone_re.search(ab_text) or email_re.search(ab_text) or "address" in ab_text.lower() or "care" in ab_text.lower():
                    matched_boxes.append(ab)
                    extracted_parts.append(ab_text)
                    if len(extracted_parts) >= 3:
                        break

            combined_val = " | ".join(dict.fromkeys(extracted_parts))
            raw_ocr_conf = sum(float(b.get("confidence", 0.0)) for b in matched_boxes) / max(len(matched_boxes), 1)
            evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
            status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
            conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, supporting_tokens_count=len(matched_boxes))

            return FieldCandidate(
                field_name=field_name,
                display_name=display_name,
                value=combined_val,
                raw_value=" \n ".join([b.get("text", "") for b in matched_boxes]),
                normalized_value=combined_val,
                confidence=conf,
                raw_ocr_confidence=round(raw_ocr_conf, 4),
                status=status,
                source_image_id=image_id,
                source_image_role=image_role,
                source_ocr_ids=evidence["source_ocr_ids"],
                evidence=evidence,
                bounding_box=evidence["enclosing_box"],
                extraction_method="CONTEXTUAL_CONTACT_GROUPING"
            )

        # Standalone toll-free or feedback email with contextual prefix
        for box in boxes:
            text = box.get("text", "")
            if re.search(r'\b(?:1800[-\s]?\d{3}[-\s]?\d{3,4}|feedback@|customercare@)\b', text, re.IGNORECASE):
                matched_boxes = [box]
                raw_ocr_conf = float(box.get("confidence", 0.0))
                evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=False, is_canonical_format=True)

                return FieldCandidate(
                    field_name=field_name,
                    display_name=display_name,
                    value=text.strip(),
                    raw_value=text,
                    normalized_value=text.strip(),
                    confidence=conf,
                    raw_ocr_confidence=raw_ocr_conf,
                    status=status,
                    source_image_id=image_id,
                    source_image_role=image_role,
                    source_ocr_ids=evidence["source_ocr_ids"],
                    evidence=evidence,
                    bounding_box=evidence["enclosing_box"],
                    extraction_method="TOLLFREE_OR_EMAIL_PATTERN"
                )

        return FieldCandidate(field_name=field_name, display_name=display_name, status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role)

    # -------------------------------------------------------------
    # 11. COUNTRY OF ORIGIN EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_country_of_origin(cls, boxes: List[Dict[str, Any]], image_id: Optional[int] = None, image_role: str = "front") -> FieldCandidate:
        field_name = "COUNTRY_OF_ORIGIN"
        display_name = "Country of Origin"

        country_re = re.compile(
            r'\b(?:COUNTRY\s+OF\s+ORIGIN|MADE\s+IN|PRODUCT\s+OF|MANUFACTURED\s+IN)\s*[:.-]?\s*([A-Za-z\s]+)',
            re.IGNORECASE
        )

        for box in boxes:
            text = box.get("text", "")
            match = country_re.search(text)
            if match:
                country_str = match.group(1).strip()
                # Clean extraneous words if any
                country_clean = re.split(r'[,.\n\r]', country_str)[0].strip()
                if country_clean and len(country_clean) >= 3:
                    raw_ocr_conf = float(box.get("confidence", 0.0))
                    evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                    status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                    conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True)

                    return FieldCandidate(
                        field_name=field_name,
                        display_name=display_name,
                        value=country_clean.title(),
                        raw_value=box.get("text"),
                        normalized_value=country_clean.title(),
                        confidence=conf,
                        raw_ocr_confidence=raw_ocr_conf,
                        status=status,
                        source_image_id=image_id,
                        source_image_role=image_role,
                        source_ocr_ids=evidence["source_ocr_ids"],
                        evidence=evidence,
                        bounding_box=evidence["enclosing_box"],
                        extraction_method="REGEX_COUNTRY_CONTEXT"
                    )

        # Multi-box: "Country of Origin:" on one line, "India" on adjacent line
        anchor_re = re.compile(r'\b(?:COUNTRY\s+OF\s+ORIGIN|MADE\s+IN)\b', re.IGNORECASE)
        for box in boxes:
            text = box.get("text", "")
            if anchor_re.search(text):
                adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=150, max_y_gap=40)
                if adj_boxes:
                    cand = adj_boxes[0]
                    c_clean = cand.get("text", "").strip()
                    if c_clean and len(c_clean) >= 3:
                        matched_boxes = [box, cand]
                        raw_ocr_conf = (float(box.get("confidence", 0.0)) + float(cand.get("confidence", 0.0))) / 2.0
                        evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                        status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                        conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, supporting_tokens_count=2)

                        return FieldCandidate(
                            field_name=field_name,
                            display_name=display_name,
                            value=c_clean.title(),
                            raw_value=f"{text} {c_clean}",
                            normalized_value=c_clean.title(),
                            confidence=conf,
                            raw_ocr_confidence=raw_ocr_conf,
                            status=status,
                            source_image_id=image_id,
                            source_image_role=image_role,
                            source_ocr_ids=evidence["source_ocr_ids"],
                            evidence=evidence,
                            bounding_box=evidence["enclosing_box"],
                            extraction_method="SPATIAL_PROXIMITY_MERGE"
                        )

        return FieldCandidate(field_name=field_name, display_name=display_name, status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role)

    # -------------------------------------------------------------
    # 12. PRODUCT NAME EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_product_name(cls, boxes: List[Dict[str, Any]], image_id: Optional[int] = None, image_role: str = "front") -> FieldCandidate:
        field_name = "PRODUCT_NAME"
        display_name = "Product / Commodity Name"

        label_re = re.compile(r'\b(?:PRODUCT\s+NAME|COMMODITY|ITEM|BRAND|PRODUCT\s+TITLE)\s*[:.-]?\s*(.+)', re.IGNORECASE)

        # 1. Explicit label cue
        for box in boxes:
            text = box.get("text", "")
            match = label_re.search(text)
            if match:
                val = match.group(1).strip()
                if len(val) >= 2:
                    raw_ocr_conf = float(box.get("confidence", 0.0))
                    evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                    status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                    conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True)

                    return FieldCandidate(
                        field_name=field_name,
                        display_name=display_name,
                        value=val,
                        raw_value=box.get("text"),
                        normalized_value=val,
                        confidence=conf,
                        raw_ocr_confidence=raw_ocr_conf,
                        status=status,
                        source_image_id=image_id,
                        source_image_role=image_role,
                        source_ocr_ids=evidence["source_ocr_ids"],
                        evidence=evidence,
                        bounding_box=evidence["enclosing_box"],
                        extraction_method="EXPLICIT_PRODUCT_LABEL"
                    )

        # 2. Cautious heuristic for prominent top text on FRONT panel ONLY
        if image_role.lower() == "front" and boxes:
            sorted_boxes = sorted(boxes, key=lambda b: (
                -b.get("bounding_box", {}).get("h", 0),  # largest font/box height
                b.get("bounding_box", {}).get("y", 0)    # closest to top
            ))
            for top_box in sorted_boxes[:3]:
                text = top_box.get("text", "").strip()
                # Exclude obvious numbers, dates, or other statutory markers
                if any(re.search(pat, text, re.IGNORECASE) for pat in [
                    r'\bMRP\b', r'\bNET\b', r'\bMFG\b', r'\bPKD\b', r'\bEXP\b', r'\bBATCH\b', r'^\d+$'
                ]):
                    continue
                if len(text) >= 4 and float(top_box.get("confidence", 0.0)) >= 0.70:
                    raw_ocr_conf = float(top_box.get("confidence", 0.0))
                    evidence = EvidenceMatcher.build_evidence([top_box], source_image_id=image_id, source_image_role=image_role)
                    conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=False, supporting_tokens_count=1)

                    return FieldCandidate(
                        field_name=field_name,
                        display_name=display_name,
                        value=text,
                        raw_value=text,
                        normalized_value=text,
                        confidence=round(conf * 0.85, 4), # slight heuristic discount
                        raw_ocr_confidence=raw_ocr_conf,
                        status="FOUND" if conf >= 0.60 else "LOW_CONFIDENCE",
                        source_image_id=image_id,
                        source_image_role=image_role,
                        source_ocr_ids=evidence["source_ocr_ids"],
                        evidence=evidence,
                        bounding_box=evidence["enclosing_box"],
                        extraction_method="TOP_PROMINENT_HEURISTIC"
                    )

        return FieldCandidate(field_name=field_name, display_name=display_name, status="NOT_FOUND", source_image_id=image_id, source_image_role=image_role)
