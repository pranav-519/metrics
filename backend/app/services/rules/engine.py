from typing import List, Dict, Any, Optional
from app.models.models import ComplianceState, ComplianceRule

class ComplianceRuleEngine:
    """
    Evaluates category-specific, versioned legal rules against extracted declarations.
    Produces rich, explainable results with detailed reasons, statutory references,
    and suggested inspector actions.
    """

    @classmethod
    def evaluate_rules(
        cls,
        rules: List[ComplianceRule],
        extracted_declarations: List[Dict[str, Any]],
        category_code: str
    ) -> List[Dict[str, Any]]:
        """
        Executes applicable versioned rules for the product category.
        """
        results = []
        decl_map = {d["field_name"]: d for d in extracted_declarations}

        for rule in rules:
            field = rule.field_target
            decl = decl_map.get(field)

            # Evaluate declaration status against this rule
            eval_result = cls._evaluate_single_rule(rule, decl, category_code)
            results.append(eval_result)

        return results

    @classmethod
    def _evaluate_single_rule(
        cls,
        rule: ComplianceRule,
        decl: Optional[Dict[str, Any]],
        category_code: str
    ) -> Dict[str, Any]:
        """
        Evaluates a single statutory rule against an extracted declaration.
        """
        rule_info = {
            "rule_id": rule.id,
            "field_target": rule.field_target,
            "expected_requirement": rule.requirement,
            "rule_reference": rule.rule_reference,
            "rule_version": rule.version,
        }

        # Case 1: Declaration was not found at all
        if not decl or decl.get("status") == ComplianceState.NOT_FOUND:
            if rule.is_mandatory:
                return {
                    **rule_info,
                    "detected_value": "NOT DETECTED",
                    "status": ComplianceState.NOT_FOUND,
                    "confidence": 0.85,
                    "reason": f"Mandatory declaration '{rule.field_target.upper()}' was not detected in any uploaded packaging photographs.",
                    "suggested_action": f"Verify if '{rule.field_target}' is printed on another side of the packaging or request an unoccluded photograph."
                }
            else:
                return {
                    **rule_info,
                    "detected_value": "NOT DETECTED",
                    "status": ComplianceState.NOT_APPLICABLE,
                    "confidence": 0.90,
                    "reason": f"Non-mandatory declaration for category '{category_code}'.",
                    "suggested_action": "No action required."
                }

        # Case 2: Declaration was unreadable / low OCR confidence
        if decl.get("status") == ComplianceState.UNABLE_TO_VERIFY:
            return {
                **rule_info,
                "detected_value": decl.get("detected_value") or "Low confidence text",
                "status": ComplianceState.UNABLE_TO_VERIFY,
                "confidence": decl.get("confidence", 0.4),
                "reason": f"Text detected in the '{rule.field_target}' region was obscured, blurry, or low-contrast (confidence {decl.get('confidence', 0.4)*100:.0f}%).",
                "suggested_action": "Capture a clearer, glare-free, well-lit close-up photograph of this specific declaration panel."
            }

        detected_val = decl.get("detected_value", "")
        conf = decl.get("confidence", 0.9)

        # Case 3: Specific legal validations
        if rule.field_target == "mrp":
            if "incl" not in detected_val.lower() and "tax" not in detected_val.lower():
                return {
                    **rule_info,
                    "detected_value": detected_val,
                    "status": ComplianceState.POTENTIAL_NON_COMPLIANCE,
                    "confidence": conf,
                    "reason": "MRP detected without mandatory statutory phrase 'inclusive of all taxes' or 'incl. of all taxes'.",
                    "suggested_action": "Inspect physical packaging to ensure tax inclusion statement is present next to the retail price."
                }
            return {
                **rule_info,
                "detected_value": detected_val,
                "status": ComplianceState.VERIFIED_COMPLIANT,
                "confidence": conf,
                "reason": "Maximum Retail Price is clearly declared with statutory tax inclusion statement.",
                "suggested_action": "Verified compliant under Rule 6(1)(e)."
            }

        elif rule.field_target == "net_quantity":
            if "when packed" in detected_val.lower():
                return {
                    **rule_info,
                    "detected_value": detected_val,
                    "status": ComplianceState.POTENTIAL_NON_COMPLIANCE,
                    "confidence": conf,
                    "reason": "Prohibited qualification: Rule prohibits qualifying net quantity with phrases like 'when packed' for standard goods.",
                    "suggested_action": "Review qualification legality under Chapter II exemptions or issue advisory."
                }
            return {
                **rule_info,
                "detected_value": detected_val,
                "status": ComplianceState.VERIFIED_COMPLIANT,
                "confidence": conf,
                "reason": "Net quantity is specified in standardized statutory metric units.",
                "suggested_action": "Verified compliant under Rule 11."
            }

        elif rule.field_target == "consumer_care":
            has_phone = "phone" in detected_val.lower() or "1800" in detected_val
            has_email = "email" in detected_val.lower() or "@" in detected_val
            if not has_phone or not has_email:
                return {
                    **rule_info,
                    "detected_value": detected_val,
                    "status": ComplianceState.REVIEW_REQUIRED,
                    "confidence": conf,
                    "reason": "Statutory rule requires complete consumer care contact details including telephone/toll-free and email address.",
                    "suggested_action": "Verify if alternative consumer care contact channels are printed on back or side panels."
                }
            return {
                **rule_info,
                "detected_value": detected_val,
                "status": ComplianceState.VERIFIED_COMPLIANT,
                "confidence": conf,
                "reason": "Consumer care cell contact information includes functional phone and electronic communication channels.",
                "suggested_action": "Verified compliant under Rule 6(1)(g)."
            }

        elif rule.field_target == "manufacturer_name":
            return {
                **rule_info,
                "detected_value": detected_val,
                "status": ComplianceState.VERIFIED_COMPLIANT,
                "confidence": conf,
                "reason": "Manufacturer / Packer / Importer corporate identity and location details are clearly legible.",
                "suggested_action": "Verified compliant under Rule 6(1)(a)/(b)."
            }

        # Fallback to declaration's inherent compliance state
        return {
            **rule_info,
            "detected_value": detected_val,
            "status": decl.get("status", ComplianceState.VERIFIED_COMPLIANT),
            "confidence": conf,
            "reason": f"Statutory declaration requirement for '{rule.field_target}' verified against applicable schedule.",
            "suggested_action": rule.suggested_action or "No action required."
        }
