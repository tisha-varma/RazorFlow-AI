import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_project_root = os.path.dirname(_backend_dir)
sys.path.insert(0, _project_root)

from backend.database import Base, get_db
from backend.main import app
from backend.models import Merchant, Product, ProductVariant, CommercePolicy, Cart, CartItem

TEST_DATABASE_URL = "sqlite:///./test_razorflow.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Route state-transition persistence at import time so set_state() calls in
# tests land in the isolated test DB, never the dev database.
from backend.services import session_state_log as _ssl
from backend.services.state_machine import state_machine as _sm
_ssl.configure(TestSessionLocal, force=True)
_sm.on_transition(_ssl.record_transition)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    from fastapi.testclient import TestClient

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data(db_session):
    merchant = Merchant(name="Test Shop", email="test@test.com")
    db_session.add(merchant)
    db_session.flush()

    policy = CommercePolicy(
        merchant_id=merchant.id,
        max_transaction_amount_paise=500000,
        require_approval=True,
        max_quantity_per_item=5,
        allow_upsell=True,
        max_upsell_amount_paise=200000,
        allow_auto_retry=False,
        spending_limit_paise=1000000,
        is_active=True
    )
    db_session.add(policy)

    p1 = Product(
        merchant_id=merchant.id,
        name="RunPro Sprint",
        description="Lightweight running shoe",
        category="Running Shoes",
        base_price_paise=449900,
        tags=["running", "shoes"],
        is_active=True
    )
    p2 = Product(
        merchant_id=merchant.id,
        name="TrailBlazer X",
        description="Trail running shoe",
        category="Trail Shoes",
        base_price_paise=549900,
        tags=["trail", "shoes"],
        is_active=True
    )
    p3 = Product(
        merchant_id=merchant.id,
        name="Running Socks",
        description="Performance socks",
        category="Accessories",
        base_price_paise=49900,
        tags=["socks", "accessories"],
        is_active=True
    )
    db_session.add_all([p1, p2, p3])
    db_session.flush()

    for prod in [p1, p2]:
        for size in [8, 9, 10]:
            v = ProductVariant(
                product_id=prod.id,
                name=f"UK {size}",
                sku=f"SHO-{prod.id:03d}-{size}",
                price_paise=prod.base_price_paise,
                stock_quantity=10,
                attributes={"size": str(size)}
            )
            db_session.add(v)

    v_socks = ProductVariant(
        product_id=p3.id,
        name="M",
        sku="ACC-003-M",
        price_paise=49900,
        stock_quantity=25,
        attributes={"size": "M"}
    )
    db_session.add(v_socks)
    db_session.flush()

    p1.related_products.append(p3)
    db_session.commit()

    return {
        "merchant": merchant,
        "policy": policy,
        "p1": p1,
        "p2": p2,
        "p3": p3
    }
