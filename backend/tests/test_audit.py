import pytest


class TestAuditEndpoint:
    def _seed_trail(self, client, seed_data, session_id="audit-sess"):
        # Per-mutation policy logging was removed (trail noise); the
        # meaningful POLICY_CHECK_* comes from the approval step.
        from backend.services.state_machine import state_machine, SessionState
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": session_id, "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        state_machine.set_state(session_id, SessionState.DISCOVERING)
        state_machine.set_state(session_id, SessionState.CART_BUILDING)
        state_machine.set_state(session_id, SessionState.POLICY_CHECK)
        client.post(
            "/api/checkout/request-approval",
            json={"cart_id": cart["id"], "session_id": session_id}
        )
        return cart

    def test_mutations_do_not_spam_policy_checks(self, client, seed_data, db_session):
        from backend.models.audit import AuditEvent
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "quiet-sess", "merchant_id": 1}).json()
        add = client.post(f"/api/cart/{cart['id']}/items",
                          json={"product_id": p1.id, "quantity": 1}).json()
        client.put(f"/api/cart/{cart['id']}/items/{add['items'][0]['id']}",
                   json={"quantity": 2})
        client.delete(f"/api/cart/{cart['id']}/items/{add['items'][0]['id']}")
        policy_events = db_session.query(AuditEvent).filter(
            AuditEvent.session_id == "quiet-sess",
            AuditEvent.event_type.in_(["POLICY_CHECK_PASSED", "POLICY_CHECK_FAILED"])
        ).all()
        assert policy_events == []

    def test_session_trail_ordered(self, client, seed_data):
        self._seed_trail(client, seed_data)
        resp = client.get("/api/audit", params={"session_id": "audit-sess"})
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 1
        types = [e["event_type"] for e in events]
        assert "POLICY_CHECK_PASSED" in types
        # Chronological order
        stamps = [(e["timestamp"], e["id"]) for e in events]
        assert stamps == sorted(stamps)
        # Shape
        first = events[0]
        for key in ("id", "event_type", "event_data", "actor", "timestamp"):
            assert key in first

        policy_event = next(e for e in events if e["event_type"] == "POLICY_CHECK_PASSED")
        assert policy_event["policy_snapshot_id"]
        assert policy_event["event_data"]["policy_snapshot_id"] == policy_event["policy_snapshot_id"]
        assert policy_event["event_data"]["policy_snapshot"]["max_transaction_paise"] == 500000

    def test_session_isolation(self, client, seed_data):
        self._seed_trail(client, seed_data, session_id="audit-a")
        self._seed_trail(client, seed_data, session_id="audit-b")
        resp = client.get("/api/audit", params={"session_id": "audit-a"})
        assert resp.status_code == 200
        assert all(e["session_id"] == "audit-a" for e in resp.json())

    def test_merchant_filter(self, client, seed_data):
        self._seed_trail(client, seed_data)
        merchant_id = seed_data["merchant"].id
        resp = client.get("/api/audit", params={"merchant_id": merchant_id})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        assert all(e["merchant_id"] == merchant_id for e in resp.json())

    def test_requires_filter(self, client):
        resp = client.get("/api/audit")
        assert resp.status_code == 400

    def test_empty_session_returns_empty_list(self, client):
        resp = client.get("/api/audit", params={"session_id": "no-such-session"})
        assert resp.status_code == 200
        assert resp.json() == []


class TestHashChain:
    @pytest.mark.asyncio
    async def test_chain_verifies_clean(self, client, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        for sess in ("chain-a", "chain-b"):
            await registry.execute("add_to_cart", {
                "product_id": seed_data["p1"].id, "quantity": 1
            }, db=db_session, session_id=sess)
        resp = client.get("/api/audit/verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["break_at_id"] is None
        assert body["checked"] >= 2

    def test_tamper_detected_at_exact_row(self, client, seed_data, db_session):
        from backend.models.audit import AuditEvent
        from backend.services.audit_service import AuditService

        AuditService.log_event(
            db=db_session, event_type="CHAIN_T1", actor="system",
            merchant_id=seed_data["merchant"].id, session_id="chain-t",
            event_data={"amount": 100})
        victim = db_session.query(AuditEvent).filter(
            AuditEvent.session_id == "chain-t").one()
        victim.event_data = {"amount": 999999}
        db_session.commit()

        resp = client.get("/api/audit/verify")
        assert resp.status_code == 200
        assert resp.json()["ok"] is False
        assert resp.json()["break_at_id"] == victim.id

    @pytest.mark.asyncio
    async def test_events_carry_hashes(self, client, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        await registry.execute(
            "add_to_cart", {"product_id": seed_data["p1"].id, "quantity": 1},
            db=db_session, session_id="chain-c")
        events = client.get("/api/audit", params={"session_id": "chain-c"}).json()
        assert events, "expected audit rows for agent cart flow"
        assert all(e["event_hash"] and e["prev_hash"] for e in events)


class TestToolResults:
    @pytest.mark.asyncio
    async def test_results_stored_trimmed(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse, ToolCallResponse
        from backend.models.ai_interaction import AIInteraction
        from backend.tests.test_agent import _FakeLLMClient

        p1 = seed_data["p1"]
        agent = Agent(_FakeLLMClient([
            [ToolCallResponse("search_products", {"query": "running"}, "call_1")],
            TextResponse(text="Done."),
        ]))
        await agent.handle_message(db_session, "results-sess-1", "running shoes")

        row = db_session.query(AIInteraction).filter(
            AIInteraction.session_id == "results-sess-1").one()
        assert row.tool_calls[0]["tool_name"] == "search_products"
        results = row.tool_results
        assert results[0]["tool_name"] == "search_products"
        names = [p["name"] for p in results[0]["result"]]
        assert "RunPro Sprint" in names
        # Trimmed to first 3 of a longer list.
        assert len(results[0]["result"]) <= 3
