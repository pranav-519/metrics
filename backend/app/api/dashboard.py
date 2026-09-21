from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.session import get_db
from app.models.models import Scan, ComplianceState
from app.schemas.schemas import DashboardStatsResponse, ScanSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Computes aggregated compliance metrics for the inspection dashboard."""
    total_scans = db.query(Scan).count()
    verified_compliant = db.query(Scan).filter(Scan.overall_status == ComplianceState.VERIFIED_COMPLIANT).count()
    potential_non_compliance = db.query(Scan).filter(Scan.overall_status == ComplianceState.POTENTIAL_NON_COMPLIANCE).count()
    unable_to_verify = db.query(Scan).filter(Scan.overall_status == ComplianceState.UNABLE_TO_VERIFY).count()
    review_required = db.query(Scan).filter(Scan.overall_status == ComplianceState.REVIEW_REQUIRED).count()

    compliance_rate = round((verified_compliant / max(total_scans, 1)) * 100.0, 1)

    recent_db_scans = db.query(Scan).order_by(desc(Scan.created_at)).limit(10).all()
    recent_scans = []
    for s in recent_db_scans:
        summary = ScanSummaryResponse(
            id=s.id,
            product_name=s.product_name,
            category_id=s.category_id,
            category_name=s.category_rel.name if s.category_rel else "General",
            created_at=s.created_at,
            overall_status=s.overall_status,
            compliance_score=s.compliance_score,
            summary_verdict=s.summary_verdict,
            is_calibrated=s.is_calibrated,
            is_demo=s.is_demo,
            images_count=len(s.images)
        )
        recent_scans.append(summary)

    return DashboardStatsResponse(
        total_scans=total_scans,
        verified_compliant=verified_compliant,
        potential_non_compliance=potential_non_compliance,
        unable_to_verify=unable_to_verify,
        review_required=review_required,
        compliance_rate_percent=compliance_rate,
        recent_scans=recent_scans
    )
