from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.session import get_db
from app.models.models import ComplianceRule, ProductCategory
from app.schemas.schemas import RuleResponse

router = APIRouter(prefix="/rules", tags=["Rules"])

@router.get("", response_model=List[RuleResponse])
def get_rules(
    category_id: Optional[int] = Query(None, description="Filter rules by product category ID"),
    category_code: Optional[str] = Query(None, description="Filter rules by product category code"),
    db: Session = Depends(get_db)
):
    """
    Retrieve versioned statutory legal rules.
    Includes general rules (applicable across all commodities) and category-specific rules.
    """
    query = db.query(ComplianceRule).filter(ComplianceRule.is_active == True)

    target_cat_id = category_id
    if category_code and not target_cat_id:
        cat = db.query(ProductCategory).filter(ProductCategory.code == category_code).first()
        if cat:
            target_cat_id = cat.id

    if target_cat_id:
        # Get rules specifically for this category PLUS general rules where category_id is None
        query = query.filter(
            (ComplianceRule.category_id == target_cat_id) | (ComplianceRule.category_id == None)
        )

    rules = query.all()
    
    # Map category names
    res = []
    for r in rules:
        r_dict = RuleResponse.model_validate(r)
        if r.category_rel:
            r_dict.category_name = r.category_rel.name
        else:
            r_dict.category_name = "All Packaged Commodities"
        res.append(r_dict)

    return res

@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule_by_id(rule_id: str, db: Session = Depends(get_db)):
    """Fetch single compliance rule by its statutory ID (e.g. 'LMR-2011-R6-MRP')."""
    rule = db.query(ComplianceRule).filter(ComplianceRule.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Compliance rule record not found.")
    
    r_dict = RuleResponse.model_validate(rule)
    r_dict.category_name = rule.category_rel.name if rule.category_rel else "All Packaged Commodities"
    return r_dict
