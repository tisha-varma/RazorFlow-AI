from typing import List, Dict, Any, Callable
from backend.services.ai.llm_client import ToolDefinition


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, dict] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable
    ):
        self._tools[name] = {
            "definition": ToolDefinition(name, description, parameters),
            "handler": handler
        }

    def get_definitions(self) -> List[ToolDefinition]:
        return [t["definition"] for t in self._tools.values()]

    async def execute(self, tool_name: str, arguments: dict, db=None, session_id: str = "") -> Any:
        if tool_name not in self._tools:
            return {"error": f"Unknown tool: {tool_name}"}

        handler = self._tools[tool_name]["handler"]
        # Coerce types based on tool parameter definitions
        tool_def = self._tools[tool_name]
        if "parameters" in tool_def and "properties" in tool_def["parameters"]:
            for param_name, param_def in tool_def["parameters"]["properties"].items():
                if param_name in arguments:
                    if param_def.get("type") == "integer":
                        try:
                            arguments[param_name] = int(arguments[param_name])
                        except (ValueError, TypeError):
                            pass
                    elif param_def.get("type") == "number":
                        try:
                            arguments[param_name] = float(arguments[param_name])
                        except (ValueError, TypeError):
                            pass
        try:
            if db is not None:
                return await handler(db=db, session_id=session_id, **arguments)
            else:
                return await handler(**arguments)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())


def create_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    # Tool 1: search_products
    async def search_products(db=None, session_id="", query="", filters=None):
        from backend.services.catalog_service import CatalogService
        filters = filters or {}
        products, total = CatalogService.get_products(
            db,
            query=query or None,
            category=filters.get("category"),
            min_price=filters.get("min_price"),
            max_price=filters.get("max_price"),
            in_stock=filters.get("in_stock"),
            limit=10
        )
        return [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "base_price_paise": p.base_price_paise,
                "description": p.description,
                "tags": p.tags or [],
                "in_stock": any(v.stock_quantity > 0 for v in p.variants) if p.variants else False
            }
            for p in products
        ]

    registry.register(
        name="search_products",
        description="Search the product catalog by keyword, category, price range, and stock availability. Returns matching products.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to match against product names, descriptions, and categories"
                },
                "filters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Filter by category name"},
                        "min_price": {"type": "integer", "description": "Minimum price in paise"},
                        "max_price": {"type": "integer", "description": "Maximum price in paise"},
                        "in_stock": {"type": "boolean", "description": "Only show in-stock products"}
                    }
                }
            },
            "required": []
        },
        handler=search_products
    )

    # Tool 2: get_product
    async def get_product(db=None, session_id="", product_id=0):
        from backend.services.catalog_service import CatalogService
        product = CatalogService.get_product_by_id(db, product_id)
        if not product:
            return {"error": f"Product {product_id} not found"}
        variants = [
            {
                "id": v.id,
                "name": v.name,
                "sku": v.sku,
                "price_paise": v.price_paise,
                "stock_quantity": v.stock_quantity,
                "attributes": v.attributes
            }
            for v in product.variants
        ]
        related = [
            {
                "id": r.id,
                "name": r.name,
                "base_price_paise": r.base_price_paise,
                "category": r.category
            }
            for r in product.related_products
        ]
        return {
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "base_price_paise": product.base_price_paise,
            "description": product.description,
            "tags": product.tags or [],
            "variants": variants,
            "related_products": related
        }

    registry.register(
        name="get_product",
        description="Get detailed information about a specific product, including variants and related products.",
        parameters={
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "The ID of the product to retrieve"
                }
            },
            "required": ["product_id"]
        },
        handler=get_product
    )

    # Tool 3: check_stock
    async def check_stock(db=None, session_id="", product_id=0, variant_id=None):
        from backend.services.catalog_service import CatalogService
        in_stock, quantity, variant_name = CatalogService.check_stock(db, product_id, variant_id)
        return {
            "in_stock": in_stock,
            "quantity": quantity,
            "variant_name": variant_name
        }

    registry.register(
        name="check_stock",
        description="Check stock availability for a product, optionally for a specific variant.",
        parameters={
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "The product ID"
                },
                "variant_id": {
                    "type": "integer",
                    "description": "Optional variant ID to check specific variant stock"
                }
            },
            "required": ["product_id"]
        },
        handler=check_stock
    )

    # Tool 4: get_related_products
    async def get_related_products(db=None, session_id="", product_id=0):
        from backend.services.catalog_service import CatalogService
        products = CatalogService.get_related_products(db, product_id)
        return [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "base_price_paise": p.base_price_paise,
                "description": p.description,
                "merchant_id": p.merchant_id,
                "tags": p.tags or [],
                "is_active": p.is_active,
                "in_stock": True,
                "created_at": str(p.created_at) if hasattr(p, 'created_at') else ""
            }
            for p in products
        ]

    registry.register(
        name="get_related_products",
        description="Get products related to a given product. Useful for upsell/cross-sell recommendations.",
        parameters={
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "The product ID to find related items for"
                }
            },
            "required": ["product_id"]
        },
        handler=get_related_products
    )

    # Tool 5: create_cart
    async def create_cart(db=None, session_id="", merchant_id=1):
        from backend.services.cart_service import CartService
        cart = CartService.create_cart(db, session_id, merchant_id)
        return {
            "cart_id": cart.id,
            "session_id": cart.session_id,
            "status": cart.status,
            "items": []
        }

    registry.register(
        name="create_cart",
        description="Create a new shopping cart for the current session.",
        parameters={
            "type": "object",
            "properties": {
                "merchant_id": {
                    "type": "integer",
                    "description": "Merchant ID (default: 1)"
                }
            },
            "required": []
        },
        handler=create_cart
    )

    # Tool 6: add_to_cart
    async def add_to_cart(db=None, session_id="", cart_id=0, product_id=0, variant_id=None, quantity=1, is_upsell=False):
        from backend.services.cart_service import CartService
        from backend.services.audit_service import AuditService
        cart = CartService.add_item(db, cart_id, product_id, variant_id, quantity, is_upsell)
        if not cart:
            return {"error": "Failed to add item to cart"}
        # Log audit
        AuditService.log_event(
            db=db,
            event_type="CART_ITEM_ADDED",
            actor="ai",
            merchant_id=cart.merchant_id,
            session_id=session_id,
            event_data={
                "cart_id": cart_id,
                "product_id": product_id,
                "variant_id": variant_id,
                "quantity": quantity,
                "is_upsell": is_upsell
            },
            related_entity_type="cart",
            related_entity_id=cart_id
        )
        totals = CartService.calculate_totals(db, cart_id)
        return {
            "cart_id": cart.id,
            "status": cart.status,
            "item_count": totals["item_count"],
            "total_paise": totals["total_paise"]
        }

    registry.register(
        name="add_to_cart",
        description="Add a product to the shopping cart. Set is_upsell=true for upsell items.",
        parameters={
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "integer",
                    "description": "The cart ID"
                },
                "product_id": {
                    "type": "integer",
                    "description": "The product ID to add"
                },
                "variant_id": {
                    "type": "integer",
                    "description": "Optional variant ID"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity to add (default: 1)"
                },
                "is_upsell": {
                    "type": "boolean",
                    "description": "Whether this is an upsell item (default: false)"
                }
            },
            "required": ["cart_id", "product_id"]
        },
        handler=add_to_cart
    )

    # Tool 7: remove_from_cart
    async def remove_from_cart(db=None, session_id="", cart_id=0, item_id=0):
        from backend.services.cart_service import CartService
        from backend.services.audit_service import AuditService
        cart = CartService.remove_item(db, cart_id, item_id)
        if not cart:
            return {"error": "Failed to remove item from cart"}
        AuditService.log_event(
            db=db,
            event_type="CART_ITEM_REMOVED",
            actor="ai",
            merchant_id=cart.merchant_id,
            session_id=session_id,
            event_data={"cart_id": cart_id, "item_id": item_id},
            related_entity_type="cart",
            related_entity_id=cart_id
        )
        totals = CartService.calculate_totals(db, cart_id)
        return {
            "cart_id": cart.id,
            "status": cart.status,
            "item_count": totals["item_count"],
            "total_paise": totals["total_paise"]
        }

    registry.register(
        name="remove_from_cart",
        description="Remove an item from the shopping cart.",
        parameters={
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "integer",
                    "description": "The cart ID"
                },
                "item_id": {
                    "type": "integer",
                    "description": "The cart item ID to remove"
                }
            },
            "required": ["cart_id", "item_id"]
        },
        handler=remove_from_cart
    )

    # Tool 8: update_quantity
    async def update_quantity(db=None, session_id="", cart_id=0, item_id=0, quantity=1):
        from backend.services.cart_service import CartService
        cart = CartService.update_quantity(db, cart_id, item_id, quantity)
        if not cart:
            return {"error": "Failed to update quantity"}
        totals = CartService.calculate_totals(db, cart_id)
        return {
            "cart_id": cart.id,
            "status": cart.status,
            "item_count": totals["item_count"],
            "total_paise": totals["total_paise"]
        }

    registry.register(
        name="update_quantity",
        description="Update the quantity of an item in the cart.",
        parameters={
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "integer",
                    "description": "The cart ID"
                },
                "item_id": {
                    "type": "integer",
                    "description": "The cart item ID"
                },
                "quantity": {
                    "type": "integer",
                    "description": "New quantity"
                }
            },
            "required": ["cart_id", "item_id", "quantity"]
        },
        handler=update_quantity
    )

    # Tool 9: calculate_cart
    async def calculate_cart(db=None, session_id="", cart_id=0):
        from backend.services.cart_service import CartService
        totals = CartService.calculate_totals(db, cart_id)
        if not totals:
            return {"error": "Cart not found"}
        return totals

    registry.register(
        name="calculate_cart",
        description="Calculate the current cart totals including subtotal, total, and item breakdown.",
        parameters={
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "integer",
                    "description": "The cart ID"
                }
            },
            "required": ["cart_id"]
        },
        handler=calculate_cart
    )

    # Tool 10: check_purchase_policy
    async def check_purchase_policy(db=None, session_id="", cart_id=0):
        from backend.services.policy_engine import PolicyEngine
        from backend.models.policy import CommercePolicy
        from backend.services.audit_service import AuditService
        policy = db.query(CommercePolicy).filter(CommercePolicy.is_active == True).first()
        if not policy:
            return {"error": "No active commerce policy found"}
        result = PolicyEngine.check_purchase_policy(db, cart_id, session_id, policy)
        AuditService.log_event(
            db=db,
            event_type="POLICY_CHECK_PASSED" if result.allowed else "POLICY_CHECK_FAILED",
            actor="system",
            merchant_id=policy.merchant_id,
            session_id=session_id,
            event_data={
                "cart_id": cart_id,
                "allowed": result.allowed,
                "reason": result.reason
            },
            related_entity_type="cart",
            related_entity_id=cart_id
        )
        return result.to_dict()

    registry.register(
        name="check_purchase_policy",
        description="Check if the cart contents comply with the merchant's commerce policy. Returns allowed/blocked status.",
        parameters={
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "integer",
                    "description": "The cart ID to check"
                }
            },
            "required": ["cart_id"]
        },
        handler=check_purchase_policy
    )

    # Tool 11: generate_purchase_summary
    async def generate_purchase_summary(db=None, session_id="", cart_id=0):
        from backend.services.cart_service import CartService
        from backend.services.policy_engine import PolicyEngine
        from backend.models.policy import CommercePolicy
        totals = CartService.calculate_totals(db, cart_id)
        if not totals:
            return {"error": "Cart not found"}
        policy = db.query(CommercePolicy).filter(CommercePolicy.is_active == True).first()
        policy_result = PolicyEngine.check_purchase_policy(db, cart_id, session_id, policy) if policy else None
        return {
            "cart_id": cart_id,
            "items": totals["items"],
            "subtotal_paise": totals["subtotal_paise"],
            "total_paise": totals["total_paise"],
            "policy_allowed": policy_result.allowed if policy_result else None,
            "policy_reason": policy_result.reason if policy_result else None
        }

    registry.register(
        name="generate_purchase_summary",
        description="Generate a full purchase summary for the current cart including item details and policy check.",
        parameters={
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "integer",
                    "description": "The cart ID"
                }
            },
            "required": ["cart_id"]
        },
        handler=generate_purchase_summary
    )

    # Tool 12: request_payment_approval
    async def request_payment_approval(db=None, session_id="", cart_id=0):
        from backend.models.approval import Approval
        from backend.services.cart_service import CartService
        from backend.services.audit_service import AuditService
        from backend.models.merchant import Merchant
        totals = CartService.calculate_totals(db, cart_id)
        if not totals:
            return {"error": "Cart not found"}
        merchant = db.query(Merchant).first()
        merchant_id = merchant.id if merchant else 1
        summary_json = {
            "items": totals["items"],
            "subtotal_paise": totals["subtotal_paise"],
            "total_paise": totals["total_paise"]
        }
        approval = Approval(
            session_id=session_id,
            cart_id=cart_id,
            requested_amount_paise=totals["total_paise"],
            status="pending",
            summary_json=summary_json
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        AuditService.log_event(
            db=db,
            event_type="PAYMENT_APPROVAL_REQUESTED",
            actor="ai",
            merchant_id=merchant_id,
            session_id=session_id,
            event_data={
                "approval_id": approval.id,
                "cart_id": cart_id,
                "amount_paise": totals["total_paise"]
            },
            related_entity_type="approval",
            related_entity_id=approval.id
        )
        return {
            "approval_id": approval.id,
            "status": approval.status,
            "requested_amount_paise": approval.requested_amount_paise,
            "summary": summary_json
        }

    registry.register(
        name="request_payment_approval",
        description="Request user approval for a purchase. Creates a pending approval record that the user must explicitly approve.",
        parameters={
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "integer",
                    "description": "The cart ID"
                }
            },
            "required": ["cart_id"]
        },
        handler=request_payment_approval
    )

    return registry
