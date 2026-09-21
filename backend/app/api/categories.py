from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.models import ProductCategory
from app.schemas.schemas import CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Retrieve all active product categories."""
    categories = db.query(ProductCategory).filter(ProductCategory.is_active == True).all()
    return categories
