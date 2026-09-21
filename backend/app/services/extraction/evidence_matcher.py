from typing import List, Dict, Any, Optional

class EvidenceMatcher:
    """
    Deterministic spatial and token evidence matching service.
    Associates label detections with value detections, aggregates bounding boxes,
    and calculates explainable field-level confidence scores.
    """

    @staticmethod
    def get_box_coords(bbox: Dict[str, Any]) -> Dict[str, int]:
        """Extracts standard x1, y1, x2, y2 from varying bounding box formats."""
        if not bbox:
            return {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "x": 0, "y": 0, "w": 0, "h": 0}
        
        x1 = bbox.get("x1", bbox.get("x", 0))
        y1 = bbox.get("y1", bbox.get("y", 0))
        x2 = bbox.get("x2", x1 + bbox.get("w", 0))
        y2 = bbox.get("y2", y1 + bbox.get("h", 0))
        return {
            "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2),
            "x": int(x1), "y": int(y1), "w": int(max(0, x2 - x1)), "h": int(max(0, y2 - y1))
        }

    @classmethod
    def compute_enclosing_box(cls, boxes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Computes the minimal bounding rectangle enclosing all provided OCR boxes."""
        if not boxes:
            return {"x": 0, "y": 0, "w": 0, "h": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0}
        
        coords = [cls.get_box_coords(b.get("bounding_box", b)) for b in boxes]
        min_x1 = min(c["x1"] for c in coords)
        min_y1 = min(c["y1"] for c in coords)
        max_x2 = max(c["x2"] for c in coords)
        max_y2 = max(c["y2"] for c in coords)

        return {
            "x": min_x1,
            "y": min_y1,
            "w": max(0, max_x2 - min_x1),
            "h": max(0, max_y2 - min_y1),
            "x1": min_x1,
            "y1": min_y1,
            "x2": max_x2,
            "y2": max_y2
        }

    @classmethod
    def find_spatially_adjacent_boxes(
        cls,
        anchor_box: Dict[str, Any],
        candidate_boxes: List[Dict[str, Any]],
        max_x_gap: int = 250,
        max_y_gap: int = 120
    ) -> List[Dict[str, Any]]:
        """
        Finds candidate OCR boxes that are either on the same horizontal line to the right,
        or stacked immediately below the anchor label box.
        """
        anchor_c = cls.get_box_coords(anchor_box.get("bounding_box", anchor_box))
        anchor_line = anchor_box.get("line_number", 0)

        adjacent = []
        for cand in candidate_boxes:
            if cand == anchor_box:
                continue
            cand_c = cls.get_box_coords(cand.get("bounding_box", cand))
            cand_line = cand.get("line_number", 0)

            # Check 1: Same line to the right
            is_same_line = (
                (cand_line > 0 and cand_line == anchor_line) or
                abs(cand_c["y1"] - anchor_c["y1"]) <= 20
            )
            is_to_right = (cand_c["x1"] >= anchor_c["x1"] - 10) and (cand_c["x1"] - anchor_c["x2"] <= max_x_gap)

            if is_same_line and is_to_right:
                adjacent.append((0, cand_c["x1"], cand))
                continue

            # Check 2: Immediately below (e.g. multi-line address or value under label)
            is_below = (cand_c["y1"] >= anchor_c["y1"]) and (cand_c["y1"] - anchor_c["y2"] <= max_y_gap)
            has_x_overlap = not (cand_c["x2"] < anchor_c["x1"] - 40 or cand_c["x1"] > anchor_c["x2"] + 150)

            if is_below and has_x_overlap:
                adjacent.append((cand_c["y1"], cand_c["x1"], cand))

        # Sort by y, then x
        adjacent.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in adjacent]

    @classmethod
    def build_evidence(
        cls,
        matched_boxes: List[Dict[str, Any]],
        source_image_id: Optional[int] = None,
        source_image_role: str = "front"
    ) -> Dict[str, Any]:
        """
        Constructs a structured evidence payload preserving all OCR token IDs,
        bounding boxes, and image references.
        """
        if not matched_boxes:
            return {
                "bounding_boxes": [],
                "enclosing_box": None,
                "source_ocr_ids": [],
                "source_image_id": source_image_id,
                "source_image_role": source_image_role,
                "matched_tokens": [],
                "average_ocr_confidence": 0.0
            }

        boxes_list = [b.get("bounding_box", b) for b in matched_boxes]
        ocr_ids = [b.get("id") for b in matched_boxes if b.get("id") is not None]
        confidences = [float(b.get("confidence", 0.0)) for b in matched_boxes]
        tokens = [b.get("text", "") for b in matched_boxes if b.get("text")]
        avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

        img_id = source_image_id
        if img_id is None:
            img_id = next((b.get("image_id") for b in matched_boxes if b.get("image_id") is not None), None)

        img_role = source_image_role
        if matched_boxes and matched_boxes[0].get("image_type"):
            img_role = matched_boxes[0].get("image_type").lower()

        return {
            "bounding_boxes": boxes_list,
            "enclosing_box": cls.compute_enclosing_box(matched_boxes),
            "source_ocr_ids": ocr_ids,
            "source_image_id": img_id,
            "source_image_role": img_role,
            "matched_tokens": tokens,
            "average_ocr_confidence": avg_conf
        }

    @staticmethod
    def calculate_confidence(
        raw_ocr_confidence: float,
        has_explicit_label: bool = False,
        is_canonical_format: bool = False,
        supporting_tokens_count: int = 1,
        is_ambiguous: bool = False,
        is_low_quality: bool = False
    ) -> float:
        """
        Calculates field-level extraction confidence independently of raw OCR confidence.
        Explicit label, standard format, and multiple supporting tokens increase certainty.
        Ambiguity and low quality deduct certainty.
        """
        # Base confidence starts at raw OCR confidence
        score = raw_ocr_confidence if raw_ocr_confidence > 0 else 0.50

        # Quality adjustments
        if has_explicit_label:
            score = min(1.0, score + 0.12)
        if is_canonical_format:
            score = min(1.0, score + 0.08)
        if supporting_tokens_count > 1:
            score = min(1.0, score + 0.04)

        # Penalties
        if is_ambiguous:
            score = max(0.20, score - 0.35)
        if is_low_quality:
            score = max(0.10, score - 0.25)

        return round(min(max(score, 0.0), 1.0), 4)
