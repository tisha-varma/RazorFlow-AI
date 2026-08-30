from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from backend.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(String(100), default="demo_customer", nullable=False)
    session_id = Column(String(100), index=True, nullable=False)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    subtotal_paise = Column(Integer, nullable=False)
    total_paise = Column(Integer, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, paid, failed, cancelled
    is_ai_assisted = Column(Boolean, default=True, nullable=False)
    upsell_revenue_paise = Column(Integer, default=0, nullable=False)
    razorpay_order_id = Column(String(100), index=True, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("RazorpayPayment", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_paise = Column(Integer, nullable=False)
    total_paise = Column(Integer, nullable=False)
    is_upsell = Column(Boolean, default=False, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
