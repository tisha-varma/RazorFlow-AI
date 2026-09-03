import json
import time
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.services.ai.llm_client import LLMClient, TextResponse, ToolCallResponse
from backend.services.ai.tool_registry import ToolRegistry, create_tool_registry
from backend.services.ai.prompts import SYSTEM_PROMPT
from backend.services.state_machine import state_machine, SessionState
from backend.models.ai_interaction import AIInteraction
from backend.services.audit_service import AuditService


class Agent:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.tool_registry = create_tool_registry()
        self._history: Dict[str, List[Dict[str, Any]]] = {}

    def _get_history(self, session_id: str) -> List[Dict[str, Any]]:
        if session_id not in self._history:
            self._history[session_id] = []
        return self._history[session_id]

    def _trim_history(self, session_id: str, max_messages: int = 20):
        history = self._get_history(session_id)
        if len(history) > max_messages:
            self._history[session_id] = history[-max_messages:]

    async def handle_message(
        self,
        db: Session,
        session_id: str,
        message: str,
        merchant_id: int = 1
    ) -> Dict[str, Any]:
        start_time = time.time()
        tool_calls_log = []

        # Log user intent
        AuditService.log_event(
            db=db,
            event_type="USER_INTENT_RECEIVED",
            actor="user",
            merchant_id=merchant_id,
            session_id=session_id,
            event_data={"message": message}
        )

        # Determine state transition
        current_state = state_machine.get_state(session_id)
        if current_state == SessionState.IDLE:
            state_machine.set_state(session_id, SessionState.DISCOVERING)

        # Load conversation history and add new user message
        history = self._get_history(session_id)
        history.append({"role": "user", "content": message})

        # Work on a copy for the LLM call (tool results are per-iteration)
        messages = list(history)

        max_iterations = 6
        final_text = ""
        products_found = []
        upsell_products = []
        cart_data = None

        for iteration in range(max_iterations):
            response = await self.llm_client.generate(
                messages=messages,
                tools=self.tool_registry.get_definitions(),
                system_prompt=SYSTEM_PROMPT
            )

            if isinstance(response, TextResponse):
                # Try to parse text that looks like a tool call (some models emit JSON)
                parsed = None
                try:
                    parsed = json.loads(response.text.strip())
                except (json.JSONDecodeError, TypeError):
                    # Try to find JSON block embedded in text
                    import re
                    match = re.search(r'\{[^{}]*"name"\s*:\s*"[^"]+"[^{}]*\}', response.text, re.DOTALL)
                    if match:
                        try:
                            parsed = json.loads(match.group())
                        except (json.JSONDecodeError, TypeError):
                            pass
                if parsed and isinstance(parsed, dict) and "name" in parsed:
                        args = parsed.get("parameters", parsed.get("arguments", {}))
                        # Fix common LLM mistakes: convert string IDs to int
                        for key in ("product_id", "cart_id", "quantity"):
                            if key in args and isinstance(args[key], str) and args[key].isdigit():
                                args[key] = int(args[key])
                        # Handle non-numeric product_id (e.g. "RUNPROSPRINT")
                        if "product_id" in args and isinstance(args["product_id"], str) and not args["product_id"].isdigit():
                            from backend.models.catalog import Product
                            pid_str = args["product_id"]
                            product = db.query(Product).filter(Product.name.ilike(f"%{pid_str}%")).first()
                            if product:
                                args["product_id"] = product.id
                        tc_id = f"call_{uuid.uuid4().hex[:12]}"
                        try:
                            result = await self.tool_registry.execute(
                                tool_name=parsed["name"],
                                arguments=args,
                                db=db,
                                session_id=session_id
                            )
                        except Exception as e:
                            print(f"[Agent] Tool execution failed: {e}")
                            result = f"Error: {e}"
                        tool_calls_log.append({"tool_name": parsed["name"], "arguments": args})
                        tool_result_str = json.dumps(result) if not isinstance(result, str) else result
                        messages.append({"role": "assistant", "content": response.text})
                        messages.append({"role": "tool", "tool_call_id": tc_id, "content": tool_result_str})
                        # Track state
                        if parsed["name"] == "search_products" and isinstance(result, list):
                            for p in result:
                                if p["id"] not in {x["id"] for x in products_found}:
                                    products_found.append(p)
                        if parsed["name"] in ("create_cart", "add_to_cart", "remove_from_cart", "calculate_cart"):
                            if isinstance(result, dict) and "cart_id" in result:
                                cart_data = result
                        if parsed["name"] == "search_products":
                            state_machine.set_state(session_id, SessionState.RECOMMENDING)
                        elif parsed["name"] in ("add_to_cart", "create_cart"):
                            if state_machine.get_state(session_id) in (SessionState.RECOMMENDING, SessionState.DISCOVERING):
                                state_machine.set_state(session_id, SessionState.CART_BUILDING)
                        continue
                final_text = response.text
                break

            if isinstance(response, list):
                has_text = False
                has_tool_calls = False
                for resp in response:
                    if isinstance(resp, TextResponse):
                        final_text = resp.text
                        has_text = True
                    elif isinstance(resp, ToolCallResponse):
                        has_tool_calls = True
                        tool_calls_log.append({
                            "tool_name": resp.tool_name,
                            "arguments": resp.arguments
                        })

                        # Execute tool
                        result = await self.tool_registry.execute(
                            tool_name=resp.tool_name,
                            arguments=resp.arguments,
                            db=db,
                            session_id=session_id
                        )

                        # Collect products from search results (deduplicate)
                        if resp.tool_name == "search_products" and isinstance(result, list):
                            existing_ids = {p["id"] for p in products_found}
                            for p in result:
                                if p["id"] not in existing_ids:
                                    products_found.append(p)
                                    existing_ids.add(p["id"])

                        # Collect upsell products from get_related_products
                        if resp.tool_name == "get_related_products" and isinstance(result, list):
                            existing_ids = {p["id"] for p in upsell_products}
                            for p in result:
                                if p["id"] not in existing_ids:
                                    upsell_products.append(p)
                                    existing_ids.add(p["id"])

                        # Track cart state
                        if resp.tool_name in ("create_cart", "add_to_cart", "remove_from_cart", "calculate_cart"):
                            if isinstance(result, dict) and "cart_id" in result:
                                cart_data = result

                        # Update state based on tool calls
                        if resp.tool_name == "search_products":
                            state_machine.set_state(session_id, SessionState.RECOMMENDING)
                        elif resp.tool_name in ("add_to_cart", "create_cart"):
                            if state_machine.get_state(session_id) in (SessionState.RECOMMENDING, SessionState.DISCOVERING):
                                state_machine.set_state(session_id, SessionState.CART_BUILDING)
                        elif resp.tool_name == "check_purchase_policy":
                            state_machine.set_state(session_id, SessionState.POLICY_CHECK)
                        elif resp.tool_name == "request_payment_approval":
                            state_machine.set_state(session_id, SessionState.AWAITING_APPROVAL)

                        # Add tool result to messages for next iteration
                        tool_result_str = json.dumps(result) if not isinstance(result, str) else result
                        messages.append({
                            "role": "tool",
                            "tool_call_id": resp.tool_call_id,
                            "content": tool_result_str
                        })

                if not has_text and not has_tool_calls:
                    final_text = "I'm not sure how to help with that. Could you rephrase?"
                    break
                if has_tool_calls:
                    continue
            else:
                final_text = "I encountered an issue processing your request. Please try again."
                break

        # Fallback if loop ended without text response
        if not final_text:
            if products_found:
                names = ", ".join(p["name"] for p in products_found[:3])
                final_text = f"I found these products for you: {names}. Would you like more details or want to add any to your cart?"
            elif cart_data:
                final_text = f"Your cart has been updated. It now has {cart_data.get('item_count', 0)} item(s) totaling ₹{(cart_data.get('total_paise', 0) / 100):,.0f}."
            else:
                final_text = "I'm here to help! Let me know what you're looking for."

        # Save assistant response to history
        if final_text:
            history.append({"role": "assistant", "content": final_text})
            self._trim_history(session_id)

        # Log the AI interaction
        duration_ms = int((time.time() - start_time) * 1000)
        interaction = AIInteraction(
            session_id=session_id,
            merchant_id=merchant_id,
            interaction_type="search" if any(tc.get("tool_name") == "search_products" for tc in tool_calls_log) else "recommend",
            user_message=message,
            ai_response=final_text,
            tool_calls=tool_calls_log,
            tokens_used=0,
            duration_ms=duration_ms
        )
        db.add(interaction)
        db.commit()

        current_state = state_machine.get_state(session_id)

        return {
            "response": final_text,
            "tool_calls": tool_calls_log,
            "state": current_state.value,
            "products": products_found[:10],
            "upsell_products": upsell_products[:5],
            "cart": cart_data
        }
