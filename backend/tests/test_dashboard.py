from datetime import datetime, timedelta


def _seed_orders(db_session, seed_data):
    from backend.models.cart import Cart
    from backend.models.order import Order, OrderItem
    from backend.models.ai_interaction import AIInteraction

    merchant = seed_data["merchant"]
    p1 = seed_data["p1"]
    p3 = seed_data["p3"]
    carts = []
    for i in range(4):
        c = Cart(session_id=f"dash-s{i}", merchant_id=merchant.id, status="checked_out")
        db_session.add(c)
        carts.append(c)
    db_session.flush()

    def item(order, product, qty, upsell):
        db_session.add(OrderItem(
            order_id=order.id, product_id=product.id, variant_id=None,
            product_name=product.name, quantity=qty,
            unit_price_paise=product.base_price_paise,
            total_paise=product.base_price_paise * qty, is_upsell=upsell
        ))

    # Explicit timestamps on the SAME clock the endpoint uses for its
    # "today" boundary (DB server_default is UTC, app uses local time -
    # mixing them flakes near midnight).
    now = datetime.now()
    yesterday = now - timedelta(days=2)

    o1 = Order(order_number="DASH-1", merchant_id=merchant.id, customer_id="c",
               session_id="dash-s0", cart_id=carts[0].id, subtotal_paise=449900,
               total_paise=449900, status="paid", is_ai_assisted=True,
               upsell_revenue_paise=0, created_at=now)
    o2 = Order(order_number="DASH-2", merchant_id=merchant.id, customer_id="c",
               session_id="dash-s1", cart_id=carts[1].id, subtotal_paise=499800,
               total_paise=499800, status="paid", is_ai_assisted=True,
               upsell_revenue_paise=49900, created_at=now)
    o3 = Order(order_number="DASH-3", merchant_id=merchant.id, customer_id="c",
               session_id="dash-s2", cart_id=carts[2].id, subtotal_paise=299900,
               total_paise=299900, status="paid", is_ai_assisted=False,
               upsell_revenue_paise=0, created_at=yesterday)
    o4 = Order(order_number="DASH-4", merchant_id=merchant.id, customer_id="c",
               session_id="dash-s3", cart_id=carts[3].id, subtotal_paise=449900,
               total_paise=449900, status="failed", is_ai_assisted=True,
               upsell_revenue_paise=0)
    db_session.add_all([o1, o2, o3, o4])
    db_session.flush()

    item(o1, p1, 1, False)
    item(o2, p1, 1, False)
    item(o2, p3, 1, True)
    item(o3, p1, 1, False)
    # NOTE: o3 unit total (449900) intentionally differs from its order total
    # (299900) - the dashboard trusts Order.total_paise, items feed the table.

    for sess in ("dash-s0", "dash-s1", "dash-s1", "dash-s2"):
        db_session.add(AIInteraction(
            session_id=sess, merchant_id=merchant.id, interaction_type="search",
            user_message="hi", ai_response="hello", tool_calls=[]
        ))
    db_session.commit()
    return merchant


class TestDashboardSummary:
    def test_all_time_math(self, client, db_session, seed_data):
        merchant = _seed_orders(db_session, seed_data)
        resp = client.get("/api/dashboard/summary", params={"merchant_id": merchant.id})
        assert resp.status_code == 200
        all_time = resp.json()["all_time"]
        # Hand calc: 449900 + 499800 + 299900 = 1249600 over 3 paid orders.
        assert all_time["total_revenue_paise"] == 1249600
        assert all_time["order_count"] == 3
        assert all_time["ai_assisted_orders"] == 2
        assert all_time["upsell_revenue_paise"] == 49900
        assert all_time["upsell_pct"] == round(49900 / 1249600 * 100, 1)
        assert all_time["avg_order_value_paise"] == 1249600 // 3
        # Baseline = real orders minus their upsell portion, labeled honestly.
        assert all_time["baseline_label"] == "Baseline: AI orders excluding upsell items"
        assert all_time["baseline_revenue_paise"] == 1249600 - 49900
        assert all_time["baseline_aov_paise"] == (1249600 - 49900) // 3
        assert all_time["orders_with_upsell"] == 1
        assert all_time["aov_uplift_pct"] == round(
            (1249600 // 3 - (1249600 - 49900) // 3) / ((1249600 - 49900) // 3) * 100, 1
        )

    def test_today_excludes_yesterday(self, client, db_session, seed_data):
        merchant = _seed_orders(db_session, seed_data)
        today = client.get("/api/dashboard/summary", params={"merchant_id": merchant.id}).json()["today"]
        assert today["total_revenue_paise"] == 449900 + 499800
        assert today["order_count"] == 2
        assert today["upsell_pct"] == round(49900 / 949700 * 100, 1)
        assert today["avg_order_value_paise"] == 949700 // 2

    def test_conversion_uses_session_proxy(self, client, db_session, seed_data):
        merchant = _seed_orders(db_session, seed_data)
        data = client.get("/api/dashboard/summary", params={"merchant_id": merchant.id}).json()
        # 3 paid orders / 3 distinct AI sessions.
        assert data["conversion_sessions"] == 3
        assert data["conversion_rate_pct"] == 100.0
        assert "approx" not in data["conversion_note"].lower()
        assert "tracked" in data["conversion_note"].lower()

    def test_demo_prefixes_excluded_from_live(self, client, db_session, seed_data):
        from backend.models.cart import Cart
        from backend.models.order import Order
        merchant = seed_data["merchant"]
        cart = Cart(session_id="demo-x", merchant_id=merchant.id, status="checked_out")
        db_session.add(cart)
        db_session.flush()
        for number in ("HIST-900", "DEMO-9-XXXXXX"):
            db_session.add(Order(
                order_number=number, merchant_id=merchant.id, customer_id="c",
                session_id="demo-x", cart_id=cart.id, subtotal_paise=10000,
                total_paise=10000, status="paid", is_ai_assisted=True,
                upsell_revenue_paise=0))
        db_session.commit()
        all_time = client.get(
            "/api/dashboard/summary", params={"merchant_id": merchant.id}).json()["all_time"]
        assert all_time["demo_order_count"] == 2
        assert all_time["live_order_count"] == 0
        assert all_time["live_revenue_paise"] == 0

    def test_live_upsell_split(self, client, db_session, seed_data):
        merchant = _seed_orders(db_session, seed_data)
        all_time = client.get(
            "/api/dashboard/summary", params={"merchant_id": merchant.id}).json()["all_time"]
        # No HIST-* rows here: everything is live.
        assert all_time["demo_order_count"] == 0
        assert all_time["live_order_count"] == 3
        assert all_time["live_revenue_paise"] == 449900 + 499800 + 299900
        # Only o2 carries an upsell line (p3, 49900) on a live order.
        assert all_time["live_upsell_revenue_paise"] == 49900
        assert all_time["live_upsell_pct"] == round(49900 / 1249600 * 100, 1)

    def test_recent_orders_table(self, client, db_session, seed_data):
        merchant = _seed_orders(db_session, seed_data)
        data = client.get("/api/dashboard/summary", params={"merchant_id": merchant.id}).json()
        recent = data["recent_orders"]
        assert len(recent) == 4  # includes the failed order, newest first
        dash2 = next(o for o in recent if o["order_number"] == "DASH-2")
        assert dash2["total_paise"] == 499800
        assert dash2["is_ai_assisted"] is True
        assert "RunPro Sprint" in dash2["product_names"]
        assert dash2["status"] == "paid"

    def test_empty_merchant_zeroes(self, client, seed_data):
        data = client.get("/api/dashboard/summary", params={"merchant_id": 9999}).json()
        assert data["all_time"]["total_revenue_paise"] == 0
        assert data["all_time"]["avg_order_value_paise"] == 0
        assert data["conversion_rate_pct"] == 0.0
        assert data["recent_orders"] == []


def _drive(session_id, *states):
    from backend.services.state_machine import state_machine, SessionState
    assert state_machine.get_state(session_id) == SessionState.IDLE
    for name in states:
        assert state_machine.set_state(session_id, SessionState[name]) is True


class TestFunnel:
    def test_counts_match_hand_driven_sessions(self, client, seed_data):
        # f1: full journey. f2: stops at cart. f3: bounces at discovery.
        # f4: skips RECOMMENDING (DISCOVERING -> CART_BUILDING is legal).
        _drive("funnel-f1", "DISCOVERING", "RECOMMENDING", "CART_BUILDING",
               "POLICY_CHECK", "AWAITING_APPROVAL", "PAYMENT_PENDING",
               "PAYMENT_SUCCESS", "ORDER_CONFIRMED")
        _drive("funnel-f2", "DISCOVERING", "RECOMMENDING", "CART_BUILDING")
        _drive("funnel-f3", "DISCOVERING")
        _drive("funnel-f4", "DISCOVERING", "CART_BUILDING")

        data = client.get("/api/dashboard/funnel").json()
        counts = {s["stage"]: s["sessions"] for s in data["stages"]}
        assert counts == {
            "DISCOVERING": 4,
            "RECOMMENDING": 3,  # f4 counts via later CART_BUILDING reach
            "CART_BUILDING": 3,
            "AWAITING_APPROVAL": 1,
            "PAYMENT_PENDING": 1,
            "ORDER_CONFIRMED": 1
        }
        drops = {s["stage"]: s["dropoff_pct_from_prev"] for s in data["stages"]}
        assert drops["DISCOVERING"] == 0.0
        assert drops["RECOMMENDING"] == 25.0
        assert drops["CART_BUILDING"] == 0.0
        assert drops["AWAITING_APPROVAL"] == round((3 - 1) / 3 * 100, 1)

    def test_monotonic_non_increasing(self, client, seed_data):
        _drive("funnel-m1", "DISCOVERING", "RECOMMENDING")
        _drive("funnel-m2", "DISCOVERING", "CART_BUILDING",
               "POLICY_CHECK", "AWAITING_APPROVAL")
        data = client.get("/api/dashboard/funnel").json()
        counts = [s["sessions"] for s in data["stages"]]
        assert all(b <= a for a, b in zip(counts, counts[1:]))

    def test_transitions_persisted(self, client, db_session, seed_data):
        from backend.models.session_state import SessionStateEvent
        _drive("funnel-p1", "DISCOVERING", "RECOMMENDING")
        rows = db_session.query(SessionStateEvent).filter(
            SessionStateEvent.session_id == "funnel-p1"
        ).order_by(SessionStateEvent.id).all()
        assert [(r.from_state, r.to_state) for r in rows] == [
            ("IDLE", "DISCOVERING"),
            ("DISCOVERING", "RECOMMENDING")
        ]

    def test_empty_funnel_zeroes(self, client):
        data = client.get("/api/dashboard/funnel", params={"merchant_id": 9999}).json()
        assert all(s["sessions"] == 0 for s in data["stages"])
