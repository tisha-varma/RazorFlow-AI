"""UAP-compatible agent catalog endpoint.

A machine-readable manifest (RFC 8615 well-known location) so an external
buyer agent can discover this merchant's catalog schema, policy constraints,
and purchase flow without scraping chat UI. This is protocol *alignment*,
not certification: it mirrors the direction of NPCI's UAP and the global
ACP/AP2/x402 race - structured discovery, explicit policy bounds, and a
payment-delegation primitive (approval-gated, server-verified Razorpay
orders, in the spirit of x402's signed payment-gating).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.merchant import Merchant
from backend.models.policy import CommercePolicy
from backend.models.product import Product

router = APIRouter(tags=["Agent Protocol"])


@router.get("/.well-known/ai-commerce.json")
def ai_commerce_manifest(db: Session = Depends(get_db)):
    merchant = db.query(Merchant).first()
    policy = db.query(CommercePolicy).filter(
        CommercePolicy.is_active == True
    ).first()
    products = db.query(Product).filter(Product.is_active == True).all()

    categories = sorted({p.category for p in products if p.category})

    return {
        "protocol": "ai-commerce/1.0",
        "uap_compatible": True,
        "notes": (
            "Structured agent discovery surface aligned with NPCI UAP and the "
            "ACP/AP2/x402 protocol direction: machine-readable catalog, "
            "explicit policy bounds, session-scoped buyer identity, and "
            "approval-gated server-verified payments as the delegation primitive."
        ),
        "merchant": {
            "id": merchant.id if merchant else 1,
            "name": merchant.name if merchant else "SprintGear India"
        },
        "catalog": {
            "product_count": len(products),
            "categories": categories,
            "currency": "INR",
            "currency_unit": "paise",
            "detail_endpoint": "/api/catalog/products/{id}",
            "related_endpoint": "/api/catalog/products/{id}/related",
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "price_paise": p.base_price_paise,
                    "currency": "INR",
                    "tags": p.tags or [],
                    "image_url": p.image_url,
                    "related_ids": [r.id for r in p.related_products]
                }
                for p in products
            ]
        },
        "policy": {
            "max_transaction_paise": policy.max_transaction_amount_paise if policy else None,
            "spending_limit_paise": policy.spending_limit_paise if policy else None,
            "max_quantity_per_item": policy.max_quantity_per_item if policy else None,
            "max_upsell_amount_paise": policy.max_upsell_amount_paise if policy else None,
            "require_approval": policy.require_approval if policy else None,
            "unit": "All money values are integers in paise (1 INR = 100 paise)."
        },
        "buyer_identity": {
            "type": "session",
            "obtain": "POST /api/agent/session",
            "scope": "Per-session carts, approvals, orders, and audit trail."
        },
        "purchase_flow": {
            "steps": [
                "discover via catalog endpoints",
                "POST /api/cart + items (policy auto-checked on every mutation)",
                "POST /api/checkout/request-approval (explicit user approval required)",
                "POST /api/payment/create-order/{approval_id} (server-side Razorpay order)",
                "POST /api/payment/verify (server-side signature check before fulfilment)"
            ],
            "delegation_primitive": (
                "Approval-gated, server-verified Razorpay orders: no payment is "
                "fulfilled without a matching server-side signature over the "
                "merchant's own order record (x402-style payment gating)."
            )
        }
    }
