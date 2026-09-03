from datetime import datetime, time
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.order import Order, OrderItem
from backend.models.ai_interaction import AIInteraction

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _period_stats(db: Session, merchant_id: int, since=None) -> dict:
    """Revenue figures over paid orders, optionally restricted to a period."""
    query = db.query(Order).filter(
        Order.merchant_id == merchant_id,
        Order.status == "paid"
    )
    if since is not None:
        query = query.filter(Order.created_at >= since)
    orders = query.all()

    order_ids = [o.id for o in orders]
    upsell_revenue = 0
    if order_ids:
        upsell_revenue = db.query(
            func.coalesce(func.sum(OrderItem.unit_price_paise * OrderItem.quantity), 0)
        ).filter(
            OrderItem.order_id.in_(order_ids),
            OrderItem.is_upsell == True
        ).scalar() or 0

    total_revenue = sum(o.total_paise for o in orders)
    count = len(orders)
    ai_count = sum(1 for o in orders if o.is_ai_assisted)

    # Baseline: the same real orders with their upsell portion removed.
    # This is derived from actual order data - not a separate control group
    # (there is no non-AI baseline in this build), and it is labeled as such.
    baseline_revenue = total_revenue - int(upsell_revenue)
    baseline_aov = baseline_revenue // count if count else 0
    aov = total_revenue // count if count else 0
    orders_with_upsell = 0
    if order_ids:
        orders_with_upsell = db.query(
            func.count(func.distinct(OrderItem.order_id))
        ).filter(
            OrderItem.order_id.in_(order_ids),
            OrderItem.is_upsell == True
        ).scalar() or 0
    return {
        "total_revenue_paise": total_revenue,
        "order_count": count,
        "ai_assisted_orders": ai_count,
        "upsell_revenue_paise": int(upsell_revenue),
        "upsell_pct": round(upsell_revenue / total_revenue * 100, 1) if total_revenue else 0.0,
        "avg_order_value_paise": aov,
        "baseline_label": "Baseline: AI orders excluding upsell items",
        "baseline_revenue_paise": baseline_revenue,
        "baseline_aov_paise": baseline_aov,
        "orders_with_upsell": int(orders_with_upsell),
        "aov_uplift_pct": round((aov - baseline_aov) / baseline_aov * 100, 1) if baseline_aov else 0.0
    }


@router.get("/summary")
def get_summary(
    merchant_id: int = Query(1, description="Merchant ID"),
    db: Session = Depends(get_db)
):
    """Merchant revenue dashboard (paid orders only, read-only)."""
    today_start = datetime.combine(datetime.now().date(), time.min)

    sessions = db.query(func.count(func.distinct(AIInteraction.session_id))).filter(
        AIInteraction.merchant_id == merchant_id
    ).scalar() or 0
    paid_count = db.query(func.count(Order.id)).filter(
        Order.merchant_id == merchant_id,
        Order.status == "paid"
    ).scalar() or 0

    recent = (
        db.query(Order)
        .filter(Order.merchant_id == merchant_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(20)
        .all()
    )

    return {
        "merchant_id": merchant_id,
        "all_time": _period_stats(db, merchant_id),
        "today": _period_stats(db, merchant_id, since=today_start),
        "conversion_sessions": sessions,
        "conversion_rate_pct": round(paid_count / sessions * 100, 1) if sessions else 0.0,
        "conversion_note": (
            "Approximation: paid orders divided by distinct AI sessions "
            "(AIInteraction rows). Sessions that never touched the assistant "
            "are not counted."
        ),
        "recent_orders": [
            {
                "id": o.id,
                "order_number": o.order_number,
                "product_names": [i.product_name for i in o.items],
                "total_paise": o.total_paise,
                "is_ai_assisted": o.is_ai_assisted,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None
            }
            for o in recent
        ]
    }


FUNNEL_STAGES = [
    "DISCOVERING",
    "RECOMMENDING",
    "CART_BUILDING",
    "AWAITING_APPROVAL",
    "PAYMENT_PENDING",
    "ORDER_CONFIRMED",
]


@router.get("/funnel")
def get_funnel(
    merchant_id: int = Query(1, description="Merchant ID"),
    db: Session = Depends(get_db)
):
    """Commerce funnel: distinct sessions reaching each stage.

    A stage counts sessions reaching it OR any later stage (cumulative
    reach), so counts are monotonically non-increasing by construction -
    sessions may legally skip stages (e.g. DISCOVERING -> CART_BUILDING).
    """
    from backend.models.session_state import SessionStateEvent

    reached: dict[str, set] = {}
    rows = db.query(
        SessionStateEvent.session_id, SessionStateEvent.to_state
    ).filter(
        (SessionStateEvent.merchant_id == merchant_id)
        | (SessionStateEvent.merchant_id.is_(None))
    ).all()
    for session_id, to_state in rows:
        reached.setdefault(to_state, set()).add(session_id)

    stages = []
    prev = None
    for i, stage in enumerate(FUNNEL_STAGES):
        later = set()
        for s in FUNNEL_STAGES[i:]:
            later |= reached.get(s, set())
        count = len(later)
        dropoff_pct = (
            round((prev - count) / prev * 100, 1) if prev else 0.0
        )
        stages.append({
            "stage": stage,
            "sessions": count,
            "dropoff_pct_from_prev": dropoff_pct
        })
        prev = count

    return {
        "merchant_id": merchant_id,
        "stages": stages,
        "note": "Cumulative reach per stage (this stage or any later one), from persisted state transitions."
    }
