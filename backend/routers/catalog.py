from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.catalog import ProductOut, ProductDetailOut, ProductListOut, ProductCreate, ProductUpdate
from backend.services.catalog_service import CatalogService
from typing import Optional, List

router = APIRouter(prefix="/catalog", tags=["Catalog"])

@router.get("/products", response_model=ProductListOut)
def list_products(
    query: Optional[str] = Query(None, description="Search products by name/description/category"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[int] = Query(None, description="Minimum price in paise"),
    max_price: Optional[int] = Query(None, description="Maximum price in paise"),
    in_stock: Optional[bool] = Query(None, description="Only show in-stock products"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    products, total = CatalogService.get_products(
        db, query, category, min_price, max_price, in_stock, page, limit
    )
    return {"products": products, "total": total}

@router.get("/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    return CatalogService.get_categories(db)

@router.get("/products/{id}", response_model=ProductDetailOut)
def get_product(id: int, db: Session = Depends(get_db)):
    product = CatalogService.get_product_by_id(db, id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Product with id {id} not found"
        )
    return product

@router.get("/products/{id}/stock")
def get_product_stock(
    id: int, 
    variant_id: Optional[int] = Query(None), 
    db: Session = Depends(get_db)
):
    # Verify product exists
    product = CatalogService.get_product_by_id(db, id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Product with id {id} not found"
        )
        
    in_stock, quantity, name = CatalogService.check_stock(db, id, variant_id)
    return {
        "product_id": id,
        "variant_id": variant_id,
        "variant_name": name,
        "in_stock": in_stock,
        "quantity": quantity
    }

@router.get("/products/{id}/related", response_model=List[ProductOut])
def get_related(id: int, db: Session = Depends(get_db)):
    product = CatalogService.get_product_by_id(db, id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )
    # Same rule-based fallback as the agent path (curated relations first,
    # then tag-matched Accessories) so UI-driven adds always get upsells.
    products, _ = CatalogService.get_related_products_with_source(db, id)
    return products

@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate, 
    merchant_id: int = Query(1, description="Hardcoded merchant ID for demo"), 
    db: Session = Depends(get_db)
):
    return CatalogService.create_product(db, merchant_id, product_data)

@router.put("/products/{id}", response_model=ProductOut)
def update_product(id: int, product_data: ProductUpdate, db: Session = Depends(get_db)):
    product = CatalogService.update_product(db, id, product_data)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_44_NOT_FOUND, 
            detail=f"Product with id {id} not found"
        )
    return product

@router.delete("/products/{id}", status_code=status.HTTP_200_OK)
def delete_product(id: int, db: Session = Depends(get_db)):
    success = CatalogService.delete_product(db, id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Product with id {id} not found"
        )
    return {"deleted": True, "product_id": id}
