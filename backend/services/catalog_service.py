from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.models import Product, ProductVariant
from backend.schemas.catalog import ProductCreate, ProductUpdate
from typing import Optional, List

class CatalogService:
    @staticmethod
    def get_products(
        db: Session,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        in_stock: Optional[bool] = None,
        page: int = 1,
        limit: int = 20
    ) -> tuple[List[Product], int]:
        db_query = db.query(Product).filter(Product.is_active == True)

        if query:
            search_pattern = f"%{query}%"
            db_query = db_query.filter(
                or_(
                    Product.name.ilike(search_pattern),
                    Product.description.ilike(search_pattern),
                    Product.category.ilike(search_pattern)
                )
            )

        if category:
            db_query = db_query.filter(Product.category.ilike(category))

        if min_price is not None:
            db_query = db_query.filter(Product.base_price_paise >= min_price)

        if max_price is not None:
            db_query = db_query.filter(Product.base_price_paise <= max_price)

        if in_stock:
            db_query = db_query.join(ProductVariant).filter(ProductVariant.stock_quantity > 0).distinct()

        total = db_query.count()
        offset = (page - 1) * limit
        products = db_query.offset(offset).limit(limit).all()

        return products, total

    @staticmethod
    def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
        return db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()

    @staticmethod
    def check_stock(db: Session, product_id: int, variant_id: Optional[int] = None) -> tuple[bool, int, Optional[str]]:
        if variant_id:
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == variant_id, 
                ProductVariant.product_id == product_id
            ).first()
            if not variant:
                return False, 0, None
            return variant.stock_quantity > 0, variant.stock_quantity, variant.name
        else:
            variants = db.query(ProductVariant).filter(ProductVariant.product_id == product_id).all()
            if not variants:
                return False, 0, None
            total_stock = sum(v.stock_quantity for v in variants)
            return total_stock > 0, total_stock, None

    @staticmethod
    def get_related_products_with_source(
        db: Session, product_id: int
    ) -> tuple[List[Product], str]:
        """Related products plus which rule produced them.

        Source is "explicit" when curated product_relations rows exist,
        "tag_fallback" when the rule-based fallback below was used, or
        "none" when the product is missing / nothing matches. No ML -
        the fallback is a plain explainable rule: Accessories sharing at
        least one tag with the primary product, limit 2.
        """
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            print(f"[CATALOG] related({product_id}): none (product not found)")
            return [], "none"

        explicit = list(product.related_products or [])
        if explicit:
            print(f"[CATALOG] related({product_id}): explicit ({len(explicit)})")
            return explicit, "explicit"

        primary_tags = set(product.tags or [])
        fallback: List[Product] = []
        if primary_tags:
            candidates = db.query(Product).filter(
                Product.category.ilike("Accessories"),
                Product.id != product_id,
                Product.is_active == True
            ).all()
            for acc in candidates:
                if primary_tags.intersection(set(acc.tags or [])):
                    fallback.append(acc)
                    if len(fallback) == 2:
                        break
        print(f"[CATALOG] related({product_id}): tag_fallback ({len(fallback)})")
        return fallback, "tag_fallback"

    @staticmethod
    def get_related_products(db: Session, product_id: int) -> List[Product]:
        products, _ = CatalogService.get_related_products_with_source(db, product_id)
        return products

    @staticmethod
    def get_categories(db: Session) -> List[str]:
        categories = db.query(Product.category).filter(Product.is_active == True).distinct().all()
        return [c[0] for c in categories if c[0]]

    @staticmethod
    def create_product(db: Session, merchant_id: int, product_data: ProductCreate) -> Product:
        # Create product
        prod = Product(
            merchant_id=merchant_id,
            name=product_data.name,
            description=product_data.description,
            ai_description=product_data.ai_description or f"Product: {product_data.name}. Category: {product_data.category}.",
            category=product_data.category,
            base_price_paise=product_data.base_price_paise,
            image_url=product_data.image_url,
            tags=product_data.tags,
            is_active=product_data.is_active
        )
        db.add(prod)
        db.flush()

        # Create variants
        for var_data in product_data.variants:
            variant = ProductVariant(
                product_id=prod.id,
                name=var_data.name,
                sku=var_data.sku,
                price_paise=var_data.price_paise,
                stock_quantity=var_data.stock_quantity,
                attributes=var_data.attributes
            )
            db.add(variant)
        
        db.commit()
        db.refresh(prod)
        return prod

    @staticmethod
    def update_product(db: Session, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
        prod = db.query(Product).filter(Product.id == product_id).first()
        if not prod:
            return None
        
        update_dict = product_data.model_dump(exclude_unset=True)
        for key, val in update_dict.items():
            setattr(prod, key, val)
        
        db.commit()
        db.refresh(prod)
        return prod

    @staticmethod
    def delete_product(db: Session, product_id: int) -> bool:
        prod = db.query(Product).filter(Product.id == product_id).first()
        if not prod:
            return False
        
        # Soft delete
        prod.is_active = False
        db.commit()
        return True
