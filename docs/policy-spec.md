# RazorFlow AI — Policy Specification

## Overview

The Purchase Policy Engine is a **deterministic, backend-enforced** gate between AI intent and money movement. It reads live values from the `CommercePolicy` table — nothing is hardcoded.

## Setup Flow

### First-Run Setup (`/setup`)

On first load (no active `CommercePolicy` exists), the user is redirected to `/setup`:

1. Form presents all 7 policy fields with **prefilled defaults** (not hardcoded constants)
2. User adjusts values
3. On submit: `POST /api/policy` creates the `CommercePolicy` record
4. Redirects to the AI Buyer experience

### Policy Fields

| Field | Type | Default (prefilled) | Validation | Description |
|-------|------|---------------------|------------|-------------|
| Max Transaction Amount | ₹ input → paise | ₹5,000 | > 0, ≤ ₹100,000 | Maximum allowed single transaction |
| Require Approval | Toggle | ON (recommended locked) | — | Whether explicit user approval is needed |
| Max Quantity Per Item | Number | 5 | > 0, ≤ 100 | Maximum quantity of any single item |
| Allow Upsell | Toggle | ON | — | Whether AI can offer upsell/cross-sell |
| Max Upsell Amount | ₹ input → paise | ₹2,000 | > 0, ≤ max_transaction | Maximum total upsell value |
| Allow Auto Retry | Toggle | OFF | — | Whether failed payments auto-retry |
| Spending Limit Per Session | ₹ input → paise | ₹10,000 | > 0 | Maximum total spend in one session |

### Post-Setup Editing

Merchant can revisit `/merchant/policy` to change any field. Every change:
1. Updates the `CommercePolicy` record
2. Logs a `POLICY_CHANGED` audit event with old value, new value, field name, timestamp

### Demo Mode Reset

`POST /api/demo/reset` resets policy to the default prefilled values (₹5,000 max transaction, etc.) so demos are reproducible.

## Policy Check Logic

```python
def check_purchase_policy(cart, session_id, policy) -> PolicyResult:
    """
    Deterministic policy check. Returns ALLOWED or BLOCKED with reason.
    Called by the backend when AI requests checkout, NOT by the AI itself.
    """
    
    # 1. Cart total vs max transaction amount
    cart_total = sum(item.unit_price_paise * item.quantity for item in cart.items)
    if cart_total > policy.max_transaction_amount_paise:
        return PolicyResult(
            allowed=False,
            reason=f"Cart total ₹{cart_total/100:.2f} exceeds maximum transaction limit of ₹{policy.max_transaction_amount_paise/100:.2f}"
        )
    
    # 2. Individual item quantities
    for item in cart.items:
        if item.quantity > policy.max_quantity_per_item:
            return PolicyResult(
                allowed=False,
                reason=f"{item.product_name}: quantity {item.quantity} exceeds maximum of {policy.max_quantity_per_item} per item"
            )
    
    # 3. Session spending limit
    session_spent = get_session_total_spent(session_id)  # sum of completed orders
    if session_spent + cart_total > policy.spending_limit_paise:
        remaining = policy.spending_limit_paise - session_spent
        return PolicyResult(
            allowed=False,
            reason=f"This purchase would exceed session spending limit. Remaining budget: ₹{remaining/100:.2f}"
        )
    
    # 4. Upsell amount check
    upsell_total = sum(
        item.unit_price_paise * item.quantity 
        for item in cart.items if item.is_upsell
    )
    if upsell_total > policy.max_upsell_amount_paise:
        return PolicyResult(
            allowed=False,
            reason=f"Upsell total ₹{upsell_total/100:.2f} exceeds maximum upsell limit of ₹{policy.max_upsell_amount_paise/100:.2f}"
        )
    
    # All checks passed
    return PolicyResult(
        allowed=True,
        policy_details={
            "max_transaction": policy.max_transaction_amount_paise,
            "cart_total": cart_total,
            "remaining_budget": policy.spending_limit_paise - session_spent - cart_total,
            "approval_required": policy.require_approval,
        }
    )
```

## What Happens on BLOCKED

1. Policy engine returns `{allowed: false, reason: "..."}` to the tool registry
2. Tool registry passes result back to AI
3. AI explains the block to the user in natural language
4. AI suggests alternatives (remove items, reduce quantity, pick cheaper option)
5. Session state returns to `CART_BUILDING`
6. `POLICY_CHECK_FAILED` audit event logged

## What Happens on ALLOWED

1. Policy engine returns `{allowed: true, policy_details: {...}}`
2. If `policy.require_approval == true`: session moves to `AWAITING_APPROVAL`, approval record created
3. User sees full purchase summary + "Approve Payment — ₹X" button
4. Only after explicit user approval → `payments/create-order` can proceed
5. `POLICY_CHECK_PASSED` audit event logged

## Audit Trail for Policy Changes

```json
{
    "event_type": "POLICY_CHANGED",
    "actor": "merchant",
    "event_data": {
        "field": "max_transaction_amount_paise",
        "old_value": 500000,
        "new_value": 1000000
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```
