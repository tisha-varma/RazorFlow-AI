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
    async def search_products(db=None, session_id="", query="", filters=None, reason=None):
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
        # Prefer the LLM's own one-sentence reason; fall back to a truthful
        # deterministic statement derived from the query itself.
        fallback = f"Matched your search for '{query}'" if (query or "").strip() else None
        return [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "base_price_paise": p.base_price_paise,
                "description": p.description,
                "image_url": p.image_url,
                "tags": p.tags or [],
                "in_stock": any(v.stock_quantity > 0 for v in p.variants) if p.variants else False,
                "reason": (reason or "").strip() or fallback
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
                "reason": {
                    "type": "string",
                    "description": "REQUIRED: one sentence explaining why these results fit the customer's stated need (budget, use case, or feature match). Shown on the product card."
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
            "image_url": product.image_url,
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

    def _shaped_related(db, product_id, reason=None):
        """Related products in card-ready shape, shared by the upsell tool
        and the automatic attachment in add_to_cart."""
        from backend.services.catalog_service import CatalogService
        products, source = CatalogService.get_related_products_with_source(db, product_id)
        # Truthful fallback naming the rule that produced the match, so the
        # path (curated vs tag-based) is visible in the card reasoning text.
        primary = CatalogService.get_product_by_id(db, product_id)
        if source == "tag_fallback" and primary:
            shared = sorted(
                set(primary.tags or [])
                & {t for p in products for t in (p.tags or [])}
            )[:2]
            fallback = f"Commonly bought with {primary.category}"
            if shared:
                fallback += f" — matches {', '.join(shared)}"
        else:
            fallback = f"Complements {primary.name}" if primary else None
        return [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "base_price_paise": p.base_price_paise,
                "description": p.description,
                "image_url": p.image_url,
                "merchant_id": p.merchant_id,
                "tags": p.tags or [],
                "is_active": p.is_active,
                "in_stock": True,
                "created_at": str(p.created_at) if hasattr(p, 'created_at') else "",
                "reason": (reason or "").strip() or fallback
            }
            for p in products
        ]

    # Tool 4: get_related_products
    async def get_related_products(db=None, session_id="", product_id=0, reason=None):
        return _shaped_related(db, product_id, reason)

    registry.register(
        name="get_related_products",
        description="Get products related to a given product. Useful for upsell/cross-sell recommendations.",
        parameters={
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "The product ID to find related items for"
                },
                "reason": {
                    "type": "string",
                    "description": "REQUIRED: one sentence explaining what problem the upsell solves alongside the primary item. Shown on the upsell card."
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

    # NOTE: calculate_cart, check_purchase_policy, generate_purchase_summary,
    # and request_payment_approval are intentionally NOT LLM tools. Totals and
    # policy checks run automatically inside every cart mutation, and approvals
    # are created deterministically by CheckoutService on checkout intent.

    def _public_payload(payload: dict) -> dict:
        """Strip the ORM object before returning a payload to the LLM."""
        return {k: v for k, v in payload.items() if k != "cart"}

    # Tool 6: add_to_cart (totals + policy check included automatically)
    async def add_to_cart(db=None, session_id="", cart_id=0, product_id=0, variant_id=None, quantity=1, is_upsell=False):
        from backend.services.cart_service import CartService
        from backend.services.audit_service import AuditService
        # Resolve the cart deterministically: reuse the session's active cart,
        # or create one if none exists. Saves a create_cart round trip.
        try:
            cart_id = int(cart_id) if cart_id else 0
        except (ValueError, TypeError):
            cart_id = 0
        cart_obj = CartService.get_cart(db, cart_id) if cart_id else None
        if not cart_obj and session_id:
            cart_obj = CartService.get_active_cart_by_session(db, session_id)
        if not cart_obj:
            cart_obj = CartService.create_cart(db, session_id or "default-session", 1)
        payload = CartService.add_item(db, cart_obj.id, product_id, variant_id, quantity, is_upsell)
        if not payload:
            return {"error": "Failed to add item to cart (product or variant not found)", "cart_id": cart_obj.id}
        cart = payload["cart"]
        # Product name for a readable trail (additive context only).
        product_name = None
        for entry in payload.get("items", []):
            if entry.get("product_id") == product_id:
                product_name = entry.get("product_name")
                break
        # Log audit
        AuditService.log_event(
            db=db,
            event_type="CART_ITEM_ADDED",
            actor="ai",
            merchant_id=cart.merchant_id,
            session_id=session_id,
            event_data={
                "cart_id": cart.id,
                "product_id": product_id,
                "product_name": product_name,
                "variant_id": variant_id,
                "quantity": quantity,
                "is_upsell": is_upsell
            },
            related_entity_type="cart",
            related_entity_id=cart.id
        )
        # Automatic upsell: related items ride along with every add so the
        # panel shows them even if the LLM skips get_related_products.
        # (The added product itself is excluded - it's already in the cart.)
        related = [
            r for r in _shaped_related(db, product_id)
            if r["id"] != product_id
        ][:3]
        public = _public_payload(payload)
        public["related_products"] = related
        return public

    registry.register(
        name="add_to_cart",
        description=(
            "Add a product to the shopping cart. Set is_upsell=true for upsell items. "
            "If cart_id is omitted or 0, the session's active cart is reused or created automatically. "
            "The response always includes the cart totals, the policy check result "
            "(policy_allowed, policy_reason), and related upsell candidates "
            "(related_products) - never call separate policy or upsell tools after adding."
        ),
        parameters={
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "integer",
                    "description": "The cart ID (optional - defaults to the session's active cart)"
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
            "required": ["product_id"]
        },
        handler=add_to_cart
    )

    # Tool 7: remove_from_cart (totals + policy check included automatically)
    async def remove_from_cart(db=None, session_id="", cart_id=0, item_id=0):
        from backend.services.cart_service import CartService
        from backend.services.audit_service import AuditService
        from backend.models.cart import CartItem
        # Capture item context before deletion for a readable trail.
        doomed = db.query(CartItem).filter(
            CartItem.id == item_id, CartItem.cart_id == cart_id
        ).first() if db is not None else None
        doomed_name = doomed.product.name if doomed and doomed.product else None
        doomed_qty = doomed.quantity if doomed else None
        payload = CartService.remove_item(db, cart_id, item_id)
        if not payload:
            return {"error": "Failed to remove item from cart"}
        cart = payload["cart"]
        AuditService.log_event(
            db=db,
            event_type="CART_ITEM_REMOVED",
            actor="ai",
            merchant_id=cart.merchant_id,
            session_id=session_id,
            event_data={
                "cart_id": cart.id,
                "item_id": item_id,
                "product_name": doomed_name,
                "quantity": doomed_qty
            },
            related_entity_type="cart",
            related_entity_id=cart.id
        )
        return _public_payload(payload)

    registry.register(
        name="remove_from_cart",
        description="Remove an item from the shopping cart. The response includes updated totals and the policy check result.",
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

    # Tool 8: update_quantity (totals + policy check included automatically)
    async def update_quantity(db=None, session_id="", cart_id=0, item_id=0, quantity=1):
        from backend.services.cart_service import CartService
        payload = CartService.update_quantity(db, cart_id, item_id, quantity)
        if not payload:
            return {"error": "Failed to update quantity"}
        return _public_payload(payload)

    registry.register(
        name="update_quantity",
        description="Update the quantity of an item in the cart. The response includes updated totals and the policy check result.",
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

    return registry
