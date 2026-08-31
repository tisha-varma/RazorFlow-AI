import json
import time
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

        messages = [{"role": "user", "content": message}]

        max_iterations = 10
        final_text = ""
        products_found = []
        cart_data = None

        for iteration in range(max_iterations):
            response = await self.llm_client.generate(
                messages=messages,
                tools=self.tool_registry.get_definitions(),
                system_prompt=SYSTEM_PROMPT
            )

            if isinstance(response, TextResponse):
                final_text = response.text
                break

            if isinstance(response, list):
                has_text = False
                for resp in response:
                    if isinstance(resp, TextResponse):
                        final_text = resp.text
                        has_text = True
                    elif isinstance(resp, ToolCallResponse):
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

                        # Collect products from search results
                        if resp.tool_name == "search_products" and isinstance(result, list):
                            products_found.extend(result)

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
                            "role": "assistant",
                            "content": f"[Called tool: {resp.tool_name}]"
                        })
                        messages.append({
                            "role": "user",
                            "content": f"Tool result for {resp.tool_name}: {tool_result_str}"
                        })

                if not has_text and not tool_calls_log:
                    final_text = "I'm not sure how to help with that. Could you rephrase?"
                    break
            else:
                final_text = "I encountered an issue processing your request. Please try again."
                break

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
            "cart": cart_data
        }
