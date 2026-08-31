import pytest
import json


class TestAgentToolRegistry:
    def test_tool_registry_has_all_tools(self):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        names = registry.get_tool_names()
        expected = [
            "search_products", "get_product", "check_stock", "get_related_products",
            "create_cart", "add_to_cart", "remove_from_cart", "update_quantity",
            "calculate_cart", "check_purchase_policy", "generate_purchase_summary",
            "request_payment_approval"
        ]
        for name in expected:
            assert name in names

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
    async def test_calculate_cart_tool(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        cart = await registry.execute("create_cart", {"merchant_id": 1}, db=db_session, session_id="test-sess")
        p1 = seed_data["p1"]
        await registry.execute("add_to_cart", {
            "cart_id": cart["cart_id"],
            "product_id": p1.id,
            "quantity": 2
        }, db=db_session, session_id="test-sess")
        result = await registry.execute("calculate_cart", {"cart_id": cart["cart_id"]}, db=db_session)
        assert result["subtotal_paise"] == 449900 * 2
        assert result["item_count"] == 1

    @pytest.mark.asyncio
    async def test_check_purchase_policy_tool(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        registry = create_tool_registry()
        cart = await registry.execute("create_cart", {"merchant_id": 1}, db=db_session, session_id="test-sess")
        p1 = seed_data["p1"]
        await registry.execute("add_to_cart", {
            "cart_id": cart["cart_id"],
            "product_id": p1.id,
            "quantity": 1
        }, db=db_session, session_id="test-sess")
        result = await registry.execute("check_purchase_policy", {
            "cart_id": cart["cart_id"]
        }, db=db_session, session_id="test-sess")
        assert result["allowed"] is True

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
