# RazorFlow AI — API Contract

All endpoints are prefixed with `/api`. All money values are in **paise** (integer).

## Catalog — `/api/catalog`

### `GET /api/catalog/products`
Search/list products.
- Query: `?query=&category=&min_price=&max_price=&in_stock=true&page=1&limit=20`
- Response: `{"products": [Product], "total": int}`

### `GET /api/catalog/products/{id}`
Get product with variants and related products.
- Response: `Product` (full)

### `GET /api/catalog/products/{id}/stock`
Check stock for product or variant.
- Query: `?variant_id=`
- Response: `{"in_stock": bool, "quantity": int, "variant_name": str | null}`

### `GET /api/catalog/products/{id}/related`
Get related products.
- Response: `{"related": [Product]}`

### `GET /api/catalog/categories`
List all categories.
- Response: `{"categories": [str]}`

### `POST /api/catalog/products`
Create product.
- Body: `ProductCreate`
- Response: `Product`

### `PUT /api/catalog/products/{id}`
Update product.
- Body: `ProductUpdate`
- Response: `Product`

### `DELETE /api/catalog/products/{id}`
Delete product.
- Response: `{"deleted": true}`

---

## Agent — `/api/agent`

### `POST /api/agent/chat`
Send message to AI agent. Plain JSON request/response (no SSE).
- Body: `{"session_id": str, "message": str}`
- Response: `{"response": str, "tool_calls": [ToolCall], "state": str, "products": [Product] | null, "cart": Cart | null, "approval": Approval | null}`

### `GET /api/agent/session/{session_id}`
Get session state.
- Response: `{"state": str, "cart_id": int | null, "messages": [Message]}`

### `POST /api/agent/session`
Create new session. Spending limit read from active CommercePolicy.
- Body: `{}`
- Response: `{"session_id": str, "state": "IDLE", "spending_limit_paise": int}`

---

## Cart — `/api/cart`

### `POST /api/cart`
Create cart.
- Body: `{"session_id": str, "merchant_id": int}`
- Response: `Cart`

### `GET /api/cart/{id}`
Get cart with items and totals.
- Response: `Cart`

### `POST /api/cart/{id}/items`
Add item to cart.
- Body: `{"product_id": int, "variant_id": int | null, "quantity": int, "is_upsell": bool}`
- Response: `Cart`

### `PUT /api/cart/{id}/items/{item_id}`
Update item quantity.
- Body: `{"quantity": int}`
- Response: `Cart`

### `DELETE /api/cart/{id}/items/{item_id}`
Remove item.
- Response: `Cart`

### `GET /api/cart/{id}/calculate`
Calculate totals.
- Response: `{"subtotal_paise": int, "total_paise": int, "item_count": int, "items": [CartItemDetail]}`

---

## Policy — `/api/policy`

### `GET /api/policy`
Get active policy.
- Response: `CommercePolicy`

### `POST /api/policy`
Create policy (first-run setup).
- Body: `PolicyCreate`
- Response: `CommercePolicy`

### `PUT /api/policy/{id}`
Update policy (logs POLICY_CHANGED audit event).
- Body: `PolicyUpdate`
- Response: `CommercePolicy`

### `POST /api/policy/check`
Check cart against policy.
- Body: `{"cart_id": int, "session_id": str}`
- Response: `{"allowed": bool, "reason": str | null, "policy_details": {...}}`

---

## Checkout — `/api/checkout`

### `POST /api/checkout/summary`
Generate purchase summary.
- Body: `{"cart_id": int, "session_id": str}`
- Response: `{"summary": PurchaseSummary}`

### `POST /api/checkout/request-approval`
Request payment approval.
- Body: `{"cart_id": int, "session_id": str, "summary_json": object}`
- Response: `{"approval_id": int, "status": "pending"}`

### `POST /api/checkout/approve/{approval_id}`
User approves. Only flips approval status — does NOT create Razorpay order.
- Response: `{"status": "approved", "approval_id": int}`

### `POST /api/checkout/reject/{approval_id}`
User rejects.
- Response: `{"status": "rejected"}`

---

## Payments — `/api/payments`

### `POST /api/payments/create-order`
Create Razorpay order. **ONLY** place that creates a Razorpay order. Requires approved approval.
- Body: `{"approval_id": int}`
- Response: `{"order_id": int, "razorpay_order_id": str, "amount_paise": int, "key_id": str}`

### `POST /api/payments/verify`
Verify payment signature server-side.
- Body: `{"razorpay_order_id": str, "razorpay_payment_id": str, "razorpay_signature": str}`
- Response: `{"verified": bool, "order_status": str}`

### `GET /api/payments/{order_id}/status`
Get payment status.
- Response: `{"status": str, "razorpay_payment_id": str | null, ...}`

---

## Webhooks — `/api/webhooks`

### `POST /api/webhooks/razorpay`
Receive Razorpay webhook. Verifies signature, idempotent processing.
- Headers: `X-Razorpay-Signature`
- Body: Raw webhook payload
- Response: `200 OK`

---

## Orders — `/api/orders`

### `GET /api/orders`
List orders.
- Query: `?status=&is_ai_assisted=&page=1&limit=20`
- Response: `{"orders": [Order], "total": int}`

### `GET /api/orders/{id}`
Get order with items, payment, audit trail.
- Response: `Order` (full)

---

## Audit — `/api/audit`

### `GET /api/audit/events`
List audit events.
- Query: `?session_id=&event_type=&page=1&limit=50`
- Response: `{"events": [AuditEvent], "total": int}`

### `GET /api/audit/session/{session_id}`
Session audit trail (chronological).
- Response: `{"events": [AuditEvent]}`

---

## Analytics — `/api/analytics`

### `GET /api/analytics/dashboard`
Dashboard summary.
- Query: `?date_from=&date_to=`
- Response: `{"total_revenue_paise": int, "ai_assisted_revenue_paise": int, "upsell_revenue_paise": int, "total_orders": int, "ai_assisted_orders": int, "avg_order_value_paise": int, "conversion_rate": float}`

### `GET /api/analytics/funnel`
AI commerce funnel.
- Response: `{"stages": [{"name": str, "count": int, "drop_off_pct": float}]}`

### `GET /api/analytics/revenue-comparison`
Baseline vs AI comparison.
- Response: `{"baseline": MetricSet, "ai_assisted": MetricSet}`

---

## Merchant — `/api/merchant`

### `GET /api/merchant/profile`
- Response: `Merchant`

### `PUT /api/merchant/profile`
- Body: `MerchantUpdate`
- Response: `Merchant`

---

## Upload — `/api/upload`

### `POST /api/upload/catalog`
Upload CSV file.
- Body: `multipart/form-data` with file
- Response: `{"upload_id": int, "status": "processing"}`

### `GET /api/upload/{upload_id}/status`
Check upload status.
- Response: `{"status": str, "processed_rows": int, "total_rows": int, "errors": [str]}`

---

## Demo — `/api/demo`

### `POST /api/demo/reset`
Reset all demo data (products, orders, cart, policy to defaults).
- Response: `{"status": "reset_complete"}`

### `POST /api/demo/scenario/success`
Trigger successful purchase scenario.
- Response: `{"session_id": str}`

### `POST /api/demo/scenario/failure`
Trigger payment failure scenario.
- Response: `{"session_id": str}`

### `POST /api/demo/scenario/upsell`
Trigger upsell scenario.
- Response: `{"session_id": str}`
