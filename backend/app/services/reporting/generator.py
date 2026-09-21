from typing import List, Dict, Any
from app.models.models import ComplianceState

class ReportGeneratorService:
    """
    Synthesizes rule evaluations, OCR confidences, visual quality assessments,
    and physical measurement checks into an explainable compliance assessment.
    """

    @classmethod
    def generate_overall_assessment(
        cls,
        rule_results: List[Dict[str, Any]],
        image_qualities: List[Dict[str, Any]],
        product_name: str,
        category_name: str
    ) -> Dict[str, Any]:
        """
        Determines overall compliance state, score, summary verdict, and actionable advice.
        """
        if not rule_results:
            return {
                "overall_status": ComplianceState.REVIEW_REQUIRED,
                "compliance_score": 0.0,
                "summary_verdict": "No statutory rules evaluated for this scan.",
                "warnings": ["Evaluation pipeline produced 0 rule checks."],
                "recommended_actions": ["Upload packaging images and re-run compliance scan."]
            }

        counts = {
            ComplianceState.VERIFIED_COMPLIANT: 0,
            ComplianceState.POTENTIAL_NON_COMPLIANCE: 0,
            ComplianceState.UNABLE_TO_VERIFY: 0,
            ComplianceState.NOT_FOUND: 0,
            ComplianceState.NOT_APPLICABLE: 0,
            ComplianceState.REVIEW_REQUIRED: 0,
        }

        for r in rule_results:
            st = r["status"]
            counts[st] = counts.get(st, 0) + 1

        total_rules = len(rule_results)
        verified = counts[ComplianceState.VERIFIED_COMPLIANT]
        potential_issues = counts[ComplianceState.POTENTIAL_NON_COMPLIANCE] + counts[ComplianceState.NOT_FOUND]
        unable = counts[ComplianceState.UNABLE_TO_VERIFY]

        # Calculate weighted compliance score (0 - 100%)
        # Verified = 1.0, Unable to verify = 0.5, Review = 0.5, Potential non-compliance / Not found = 0.0
        weighted_points = (
            verified * 1.0 +
            counts[ComplianceState.NOT_APPLICABLE] * 1.0 +
            unable * 0.4 +
            counts[ComplianceState.REVIEW_REQUIRED] * 0.5
        )
        score = min(100.0, max(0.0, (weighted_points / total_rules) * 100.0))

        # Overall Status Determination
        warnings = []
        recommended_actions = []

        if potential_issues > 0:
            overall_status = ComplianceState.POTENTIAL_NON_COMPLIANCE
            summary_verdict = f"{potential_issues} potential compliance discrepancies identified under Legal Metrology Rules 2011. Inspector review advised."
            warnings.append(f"Identified {potential_issues} field(s) with non-standard formatting or missing mandatory declarations.")
            recommended_actions.append("Perform physical verification on listed discrepancies before issuing official notice.")

        elif unable > 0:
            overall_status = ComplianceState.UNABLE_TO_VERIFY
            summary_verdict = f"{unable} declaration(s) could not be reliably verified due to image blur, glare, or low OCR confidence. Never classify as missing."
            warnings.append("Certain declaration panels had insufficient visual clarity or confidence below safety threshold.")
            recommended_actions.append("Upload higher-resolution or glare-free close-up photographs for the uncertain panels.")

        elif counts[ComplianceState.REVIEW_REQUIRED] > 0:
            overall_status = ComplianceState.REVIEW_REQUIRED
            summary_verdict = "Statutory declarations detected, but manual inspector confirmation is required for specific category schedules."
            recommended_actions.append("Review highlighted declaration nuances against category exemption list.")

        else:
            overall_status = ComplianceState.VERIFIED_COMPLIANT
            summary_verdict = "All evaluated mandatory packaged commodity declarations are verified compliant under Legal Metrology Rules 2011."
            recommended_actions.append("Scan record logged into inspection audit trail. No further action needed.")

        # Check for image quality alerts
        for img_q in image_qualities:
            if img_q.get("quality_status") in ["POOR", "CRITICAL_ISSUES"]:
                warnings.append(f"Image quality alert: {img_q.get('quality_notes')}")

        return {
            "overall_status": overall_status,
            "compliance_score": round(score, 1),
            "summary_verdict": summary_verdict,
            "warnings": warnings,
            "recommended_actions": recommended_actions,
            "verified_count": verified,
            "issues_count": potential_issues,
            "uncertain_count": unable,
        }
