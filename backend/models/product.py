from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Table, JSON, func
from sqlalchemy.orm import relationship
from backend.database import Base

# Many-to-many association table for related products
product_relations = Table(
    "product_relations",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("related_product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    ai_description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)
    base_price_paise = Column(Integer, nullable=False)
    image_url = Column(String(500), nullable=True)
    tags = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    
    # Self-referential relationship for related products
    related_products = relationship(
        "Product",
        secondary=product_relations,
        primaryjoin="Product.id==product_relations.c.product_id",
        secondaryjoin="Product.id==product_relations.c.related_product_id",
        backref="related_to"
    )

class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "Size 10"
    sku = Column(String(50), unique=True, index=True, nullable=False)
    price_paise = Column(Integer, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    attributes = Column(JSON, default=dict, nullable=False)  # {"size": "10", "color": "blue"}

    product = relationship("Product", back_populates="variants")
