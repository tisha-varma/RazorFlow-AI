import pytest
import json


class TestAgentToolRegistry:
    def test_tool_registry_has_all_tools(self):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        names = registry.get_tool_names()
        # Only judgment-requiring tools are LLM-facing. Totals, policy checks,
        # summaries, and approvals run deterministically in the backend.
        expected = [
            "search_products", "get_product", "check_stock", "get_related_products",
            "create_cart", "add_to_cart", "remove_from_cart", "update_quantity"
        ]
        assert sorted(names) == sorted(expected)

    def test_deterministic_tools_not_exposed_to_llm(self):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        names = registry.get_tool_names()
        for removed in (
            "calculate_cart", "check_purchase_policy",
            "generate_purchase_summary", "request_payment_approval"
        ):
            assert removed not in names

    def test_tool_definitions_have_required_fields(self):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        for tool_def in registry.get_definitions():
            assert tool_def.name
            assert tool_def.description
            assert "type" in tool_def.parameters
            assert tool_def.parameters["type"] == "object"

    @pytest.mark.asyncio
    async def test_search_products_tool(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        result = await registry.execute("search_products", {"query": "running"}, db=db_session)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "name" in result[0]
        assert "base_price_paise" in result[0]

    @pytest.mark.asyncio
    async def test_get_product_tool(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        p1 = seed_data["p1"]
        result = await registry.execute("get_product", {"product_id": p1.id}, db=db_session)
        assert result["name"] == "RunPro Sprint"
        assert "variants" in result
        assert "related_products" in result

    @pytest.mark.asyncio
    async def test_check_stock_tool(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        p1 = seed_data["p1"]
        result = await registry.execute("check_stock", {"product_id": p1.id}, db=db_session)
        assert result["in_stock"] is True
        assert result["quantity"] > 0

    @pytest.mark.asyncio
    async def test_create_cart_tool(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        result = await registry.execute("create_cart", {"merchant_id": 1}, db=db_session, session_id="test-sess")
        assert "cart_id" in result
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_add_to_cart_tool(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        cart = await registry.execute("create_cart", {"merchant_id": 1}, db=db_session, session_id="test-sess")
        p1 = seed_data["p1"]
        result = await registry.execute("add_to_cart", {
            "cart_id": cart["cart_id"],
            "product_id": p1.id,
            "quantity": 1
        }, db=db_session, session_id="test-sess")
        assert result["item_count"] == 1
        assert result["total_paise"] == 449900

    @pytest.mark.asyncio
    async def test_calculate_totals_service(self, db_session, seed_data):
        # Totals are an internal backend call, not an LLM tool.
        from backend.services.cart_service import CartService
        cart = CartService.create_cart(db_session, "test-sess", 1)
        p1 = seed_data["p1"]
        CartService.add_item(db_session, cart.id, p1.id, quantity=2)
        totals = CartService.calculate_totals(db_session, cart.id)
        assert totals["subtotal_paise"] == 449900 * 2
        assert totals["item_count"] == 1

    @pytest.mark.asyncio
    async def test_add_to_cart_includes_policy_result(self, db_session, seed_data):
        # Policy is checked automatically on every mutation - no separate call.
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        cart = await registry.execute("create_cart", {"merchant_id": 1}, db=db_session, session_id="test-sess")
        p1 = seed_data["p1"]
        result = await registry.execute("add_to_cart", {
            "cart_id": cart["cart_id"],
            "product_id": p1.id,
            "quantity": 1
        }, db=db_session, session_id="test-sess")
        assert result["item_count"] == 1
        assert result["policy_allowed"] is True
        assert result["policy_reason"] is None

    @pytest.mark.asyncio
    async def test_add_to_cart_reports_policy_block(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        cart = await registry.execute("create_cart", {"merchant_id": 1}, db=db_session, session_id="test-sess")
        p1 = seed_data["p1"]
        result = await registry.execute("add_to_cart", {
            "cart_id": cart["cart_id"],
            "product_id": p1.id,
            "quantity": 2
        }, db=db_session, session_id="test-sess")
        # 2 x 449900 = 899800 > 500000 max transaction
        assert result["policy_allowed"] is False
        assert "exceeds" in result["policy_reason"].lower()

    @pytest.mark.asyncio
    async def test_add_to_cart_auto_resolves_session_cart(self, db_session, seed_data):
        # cart_id omitted: the session's active cart is reused/created.
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        p1 = seed_data["p1"]
        result = await registry.execute("add_to_cart", {
            "product_id": p1.id,
            "quantity": 1
        }, db=db_session, session_id="auto-cart-sess")
        assert result["item_count"] == 1
        assert result["cart_id"] > 0

    @pytest.mark.asyncio
    async def test_get_related_products_tool(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        p1 = seed_data["p1"]
        result = await registry.execute("get_related_products", {"product_id": p1.id}, db=db_session)
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        result = await registry.execute("nonexistent_tool", {})
        assert "error" in result


class _FakeLLMClient:
    """Scripted LLM: returns queued responses, counts calls. No network."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    async def generate(self, messages, tools=None, system_prompt=None):
        self.calls += 1
        idx = min(self.calls - 1, len(self.script) - 1)
        return self.script[idx]


class TestDeterministicCheckout:
    @pytest.mark.asyncio
    async def test_checkout_intent_creates_approval_in_one_llm_call(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse
        from backend.services.cart_service import CartService
        from backend.models.approval import Approval

        session_id = "checkout-intent-1"
        cart = CartService.create_cart(db_session, session_id, 1)
        p1 = seed_data["p1"]
        CartService.add_item(db_session, cart.id, p1.id, quantity=1)

        agent = Agent(_FakeLLMClient([TextResponse(text="Here is your summary.")]))
        result = await agent.handle_message(db_session, session_id, "Yes, checkout please!")

        assert agent.llm_client.calls == 1
        assert result["state"] == "AWAITING_APPROVAL"
        assert result["cart"]["approval_id"] > 0
        approval = db_session.query(Approval).filter(Approval.id == result["cart"]["approval_id"]).first()
        assert approval is not None
        assert approval.status == "pending"
        assert approval.requested_amount_paise == 449900

    @pytest.mark.asyncio
    async def test_checkout_blocked_by_policy_creates_no_approval(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse
        from backend.services.cart_service import CartService
        from backend.models.approval import Approval

        session_id = "checkout-intent-2"
        cart = CartService.create_cart(db_session, session_id, 1)
        p1 = seed_data["p1"]
        CartService.add_item(db_session, cart.id, p1.id, quantity=2)  # over limit

        agent = Agent(_FakeLLMClient([TextResponse(text="Blocked, here is why.")]))
        result = await agent.handle_message(db_session, session_id, "checkout now")

        assert agent.llm_client.calls == 1
        assert "approval_id" not in result["cart"]
        assert db_session.query(Approval).filter(Approval.session_id == session_id).count() == 0

    @pytest.mark.asyncio
    async def test_search_add_upsell_flow_bounded_llm_calls(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse, ToolCallResponse

        p1 = seed_data["p1"]
        session_id = "bounded-flow-1"
        agent = Agent(_FakeLLMClient([
            [ToolCallResponse("search_products", {"query": "running"}, "call_1")],
            [ToolCallResponse("add_to_cart", {"cart_id": 0, "product_id": p1.id, "quantity": 1}, "call_2")],
            [ToolCallResponse("get_related_products", {"product_id": p1.id}, "call_3")],
            TextResponse(text="All done."),
        ]))
        result = await agent.handle_message(db_session, session_id, "I need running shoes")

        assert agent.llm_client.calls <= 4
        assert len(result["products"]) >= 1
        assert result["cart"]["item_count"] == 1
        assert result["cart"]["policy_allowed"] is True
        assert len(result["upsell_products"]) >= 1

    def test_agent_max_iterations_bounded(self):
        import inspect
        from backend.services.ai import agent as agent_module
        source = inspect.getsource(agent_module.Agent.handle_message)
        assert "max_iterations = 4" in source


class TestProductReasons:
    @pytest.mark.asyncio
    async def test_search_products_reason_stamped(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        result = await registry.execute(
            "search_products",
            {"query": "running", "reason": "Under budget and built for marathons"},
            db=db_session
        )
        assert len(result) >= 1
        for p in result:
            assert p["reason"] == "Under budget and built for marathons"

    @pytest.mark.asyncio
    async def test_search_products_reason_fallback(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        result = await registry.execute(
            "search_products", {"query": "running"}, db=db_session
        )
        assert len(result) >= 1
        assert result[0]["reason"] == "Matched your search for 'running'"

    @pytest.mark.asyncio
    async def test_search_products_no_reason_without_query(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        result = await registry.execute("search_products", {}, db=db_session)
        assert len(result) >= 1
        assert result[0]["reason"] is None

    @pytest.mark.asyncio
    async def test_related_products_reason_stamped(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        p1 = seed_data["p1"]
        result = await registry.execute(
            "get_related_products",
            {"product_id": p1.id, "reason": "Prevents blisters on long runs"},
            db=db_session
        )
        assert len(result) >= 1
        for p in result:
            assert p["reason"] == "Prevents blisters on long runs"

    @pytest.mark.asyncio
    async def test_related_products_reason_fallback_names_primary(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        p1 = seed_data["p1"]
        result = await registry.execute(
            "get_related_products", {"product_id": p1.id}, db=db_session
        )
        assert len(result) >= 1
        assert result[0]["reason"] == "Complements RunPro Sprint"

    @pytest.mark.asyncio
    async def test_agent_attaches_call_reason_to_cards(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse, ToolCallResponse

        p1 = seed_data["p1"]
        agent = Agent(_FakeLLMClient([
            [ToolCallResponse(
                "search_products",
                {"query": "running", "reason": "Under your budget, built for distance"},
                "call_1"
            )],
            [ToolCallResponse(
                "get_related_products",
                {"product_id": p1.id, "reason": "Stops blisters on long runs"},
                "call_2"
            )],
            TextResponse(text="Done."),
        ]))
        result = await agent.handle_message(db_session, "reason-flow-1", "running shoes")

        assert result["products"][0]["reason"] == "Under your budget, built for distance"
        assert result["upsell_products"][0]["reason"] == "Stops blisters on long runs"


class TestAgentAuditTrail:
    @pytest.mark.asyncio
    async def test_search_and_recommendation_logged(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse, ToolCallResponse
        from backend.models.audit import AuditEvent

        p1 = seed_data["p1"]
        session_id = "audit-agent-1"
        agent = Agent(_FakeLLMClient([
            [ToolCallResponse("search_products", {"query": "running"}, "call_1")],
            [ToolCallResponse("get_related_products", {"product_id": p1.id}, "call_2")],
            TextResponse(text="Done."),
        ]))
        await agent.handle_message(db_session, session_id, "running shoes")

        events = {
            e.event_type: e
            for e in db_session.query(AuditEvent).filter(
                AuditEvent.session_id == session_id
            ).all()
        }
        assert "USER_INTENT_RECEIVED" in events
        assert "SEARCH_PERFORMED" in events
        assert events["SEARCH_PERFORMED"].event_data["query"] == "running"
        assert events["SEARCH_PERFORMED"].event_data["result_count"] >= 1
        assert "RECOMMENDATION_MADE" in events
        assert events["RECOMMENDATION_MADE"].event_data["product_id"] == p1.id

    @pytest.mark.asyncio
    async def test_cart_add_audit_carries_product_name(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        from backend.models.audit import AuditEvent

        registry = create_tool_registry()
        p1 = seed_data["p1"]
        result = await registry.execute("add_to_cart", {
            "product_id": p1.id,
            "quantity": 1
        }, db=db_session, session_id="audit-agent-2")
        assert result["item_count"] == 1

        event = db_session.query(AuditEvent).filter(
            AuditEvent.session_id == "audit-agent-2",
            AuditEvent.event_type == "CART_ITEM_ADDED"
        ).first()
        assert event is not None
        assert event.event_data["product_name"] == "RunPro Sprint"


class TestMoreOptions:
    @pytest.mark.asyncio
    async def test_more_options_needs_zero_llm_calls(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse

        p1 = seed_data["p1"]
        p2 = seed_data["p2"]

        class ExplodingLLM:
            async def generate(self, *a, **k):
                raise AssertionError("LLM must not be called for 'more options'")

        agent = Agent(ExplodingLLM())
        agent._last_search["more-sess-1"] = {"query": "running", "filters": {}}
        agent._seen_product_ids["more-sess-1"] = {p1.id}

        result = await agent.handle_message(db_session, "more-sess-1", "more options")
        assert result["state"] == "RECOMMENDING"
        assert len(result["products"]) >= 1
        assert all(p["id"] != p1.id for p in result["products"])
        assert p2.id in [p["id"] for p in result["products"]]
        assert "More options" in result["response"] or "more options" in result["response"]

    @pytest.mark.asyncio
    async def test_more_options_exhausted_says_so(self, db_session, seed_data):
        from backend.services.ai.agent import Agent

        p1 = seed_data["p1"]
        p2 = seed_data["p2"]
        p3 = seed_data["p3"]

        class ExplodingLLM:
            async def generate(self, *a, **k):
                raise AssertionError("LLM must not be called")

        agent = Agent(ExplodingLLM())
        agent._last_search["more-sess-2"] = {"query": "running", "filters": {}}
        agent._seen_product_ids["more-sess-2"] = {p1.id, p2.id, p3.id}

        result = await agent.handle_message(db_session, "more-sess-2", "show me more options")
        assert result["products"] == []
        assert "everything" in result["response"]

    @pytest.mark.asyncio
    async def test_more_without_history_falls_through_to_llm(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse

        agent = Agent(_FakeLLMClient([TextResponse(text="Sure, what kind?")]))
        result = await agent.handle_message(db_session, "more-sess-3", "more options")
        assert agent.llm_client.calls == 1
        assert result["response"] == "Sure, what kind?"

    @pytest.mark.asyncio
    async def test_empty_text_does_not_end_turn_blank(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse

        agent = Agent(_FakeLLMClient([
            TextResponse(text="   "),
            TextResponse(text="Hello, how can I help?"),
        ]))
        result = await agent.handle_message(db_session, "empty-sess-1", "hi")
        assert agent.llm_client.calls == 2
        assert result["response"] == "Hello, how can I help?"


class TestAutomaticUpsell:
    @pytest.mark.asyncio
    async def test_add_to_cart_carries_related(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        p1 = seed_data["p1"]
        p3 = seed_data["p3"]
        result = await registry.execute("add_to_cart", {
            "product_id": p1.id,
            "quantity": 1
        }, db=db_session, session_id="auto-upsell-1")
        assert result["item_count"] == 1
        related = result["related_products"]
        assert len(related) >= 1
        assert p3.id in [p["id"] for p in related]
        # The added product itself is never suggested back.
        assert all(p["id"] != p1.id for p in related)
        assert all(p["reason"] for p in related)
        assert all("image_url" in p for p in related)

    @pytest.mark.asyncio
    async def test_agent_upsell_without_explicit_call(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse, ToolCallResponse

        p1 = seed_data["p1"]
        p3 = seed_data["p3"]
        agent = Agent(_FakeLLMClient([
            [ToolCallResponse("add_to_cart", {"cart_id": 0, "product_id": p1.id}, "call_1")],
            TextResponse(text="Added!"),
        ]))
        result = await agent.handle_message(db_session, "auto-upsell-2", "add RunPro Sprint")
        assert result["cart"]["item_count"] == 1
        assert p3.id in [p["id"] for p in result["upsell_products"]]

    @pytest.mark.asyncio
    async def test_explicit_upsell_reason_wins(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse, ToolCallResponse

        p1 = seed_data["p1"]
        agent = Agent(_FakeLLMClient([
            [ToolCallResponse("add_to_cart", {"cart_id": 0, "product_id": p1.id}, "call_1")],
            [ToolCallResponse(
                "get_related_products",
                {"product_id": p1.id, "reason": "LLM says so"},
                "call_2"
            )],
            TextResponse(text="Done."),
        ]))
        result = await agent.handle_message(db_session, "auto-upsell-3", "add it with extras")
        reasons = {p["id"]: p.get("reason") for p in result["upsell_products"]}
        assert all(r == "LLM says so" for r in reasons.values())


class TestLiveCartSnapshot:
    @pytest.mark.asyncio
    async def test_text_turn_sees_ui_side_cart(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse
        from backend.services.cart_service import CartService

        session_id = "snapshot-sess-1"
        cart = CartService.create_cart(db_session, session_id, 1)
        CartService.add_item(db_session, cart.id, seed_data["p1"].id, quantity=1)
        CartService.add_item(db_session, cart.id, seed_data["p3"].id, quantity=1)

        agent = Agent(_FakeLLMClient([TextResponse(text="Your cart total is fine.")]))
        result = await agent.handle_message(db_session, session_id, "what is my cart value now")

        assert agent.llm_client.calls == 1
        assert result["cart"]["item_count"] == 2
        assert result["cart"]["total_paise"] == 449900 + 49900
        assert result["cart"]["policy_allowed"] is True

    def test_snapshot_note_lists_item_ids(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.cart_service import CartService
        from backend.services.ai.llm_client import TextResponse

        session_id = "snapshot-sess-2"
        cart = CartService.create_cart(db_session, session_id, 1)
        CartService.add_item(db_session, cart.id, seed_data["p3"].id, quantity=1)

        agent = Agent(_FakeLLMClient([TextResponse(text="x")]))
        snap = agent._cart_snapshot(db_session, session_id)
        assert snap is not None
        note = agent._snapshot_note(snap)
        assert "Running Socks" in note
        assert "item_id" in note
        assert "₹499" in note

    def test_empty_cart_no_snapshot(self, db_session, seed_data):
        from backend.services.ai.agent import Agent
        from backend.services.ai.llm_client import TextResponse

        agent = Agent(_FakeLLMClient([TextResponse(text="x")]))
        assert agent._cart_snapshot(db_session, "snapshot-empty") is None


class TestRemoveByName:
    @pytest.mark.asyncio
    async def test_remove_by_product_name(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        cart = await registry.execute("create_cart", {"merchant_id": 1},
                                      db=db_session, session_id="rm-sess-1")
        p3 = seed_data["p3"]
        await registry.execute("add_to_cart", {
            "cart_id": cart["cart_id"], "product_id": p3.id, "quantity": 1
        }, db=db_session, session_id="rm-sess-1")

        result = await registry.execute("remove_from_cart", {
            "cart_id": cart["cart_id"], "product_name": "socks"
        }, db=db_session, session_id="rm-sess-1")
        assert result["item_count"] == 0

    @pytest.mark.asyncio
    async def test_update_by_product_id(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        cart = await registry.execute("create_cart", {"merchant_id": 1},
                                      db=db_session, session_id="rm-sess-2")
        p1 = seed_data["p1"]
        added = await registry.execute("add_to_cart", {
            "cart_id": cart["cart_id"], "product_id": p1.id, "quantity": 1
        }, db=db_session, session_id="rm-sess-2")

        result = await registry.execute("update_quantity", {
            "cart_id": cart["cart_id"], "product_id": p1.id, "quantity": 3
        }, db=db_session, session_id="rm-sess-2")
        assert result["total_paise"] == 449900 * 3

    @pytest.mark.asyncio
    async def test_remove_no_match_errors(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        cart = await registry.execute("create_cart", {"merchant_id": 1},
                                      db=db_session, session_id="rm-sess-3")
        result = await registry.execute("remove_from_cart", {
            "cart_id": cart["cart_id"], "product_name": "nonexistent thing"
        }, db=db_session, session_id="rm-sess-3")
        assert "error" in result


class TestUpsellAuditEvents:
    @pytest.mark.asyncio
    async def test_offered_and_accepted_logged(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        from backend.models.audit import AuditEvent

        registry = create_tool_registry()
        p1 = seed_data["p1"]
        p3 = seed_data["p3"]
        cart = await registry.execute("create_cart", {"merchant_id": 1},
                                      db=db_session, session_id="upsell-audit-1")
        await registry.execute("add_to_cart", {
            "cart_id": cart["cart_id"], "product_id": p1.id, "quantity": 1
        }, db=db_session, session_id="upsell-audit-1")
        await registry.execute("add_to_cart", {
            "cart_id": cart["cart_id"], "product_id": p3.id,
            "quantity": 1, "is_upsell": True
        }, db=db_session, session_id="upsell-audit-1")

        events = {
            e.event_type: e
            for e in db_session.query(AuditEvent).filter(
                AuditEvent.session_id == "upsell-audit-1"
            ).all()
        }
        assert "UPSELL_OFFERED" in events
        assert "Running Socks" in events["UPSELL_OFFERED"].event_data["product_names"]
        assert "UPSELL_ACCEPTED" in events
        assert events["UPSELL_ACCEPTED"].event_data["product_name"] == "Running Socks"


class TestAgentPrompts:
    def test_system_prompt_exists(self):
        from backend.services.ai.prompts import SYSTEM_PROMPT
        assert "SprintGear" in SYSTEM_PROMPT
        assert "NEVER" in SYSTEM_PROMPT
        assert "paise" in SYSTEM_PROMPT

    def test_system_prompt_safety_rules(self):
        from backend.services.ai.prompts import SYSTEM_PROMPT
        assert "NEVER invent product data" in SYSTEM_PROMPT
        assert "NEVER set or override policy approval" in SYSTEM_PROMPT


class TestStateMachine:
    def test_idle_to_discovering(self):
        from backend.services.state_machine import state_machine, SessionState
        session_id = "test-sm-1"
        assert state_machine.get_state(session_id) == SessionState.IDLE
        assert state_machine.set_state(session_id, SessionState.DISCOVERING) is True
        assert state_machine.get_state(session_id) == SessionState.DISCOVERING

    def test_valid_transition(self):
        from backend.services.state_machine import state_machine, SessionState
        session_id = "test-sm-2"
        state_machine.set_state(session_id, SessionState.DISCOVERING)
        assert state_machine.set_state(session_id, SessionState.RECOMMENDING) is True

    def test_invalid_transition(self):
        from backend.services.state_machine import state_machine, SessionState
        session_id = "test-sm-3"
        assert state_machine.set_state(session_id, SessionState.PAYMENT_SUCCESS) is False
