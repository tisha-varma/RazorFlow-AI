from typing import Dict, Any

from backend.config import settings


class PaymentConfigError(RuntimeError):
    """Raised when Razorpay credentials are not configured."""


class PaymentGatewayError(RuntimeError):
    """Raised when the Razorpay API call itself fails."""


def _client():
    """Build the official Razorpay Python SDK client (test or live keys)."""
    import razorpay

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise PaymentConfigError(
            "Razorpay credentials are not configured. "
            "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
        )
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_razorpay_order(amount_paise: int, receipt_id: str, notes: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a Razorpay order server-side. Never create orders client-side.

    Per Razorpay docs, amount is in the smallest currency subunit (paise),
    receipt is a unique idempotency key (max 40 ASCII chars), and a new
    order is required for every payment attempt.
    """
    client = _client()
    payload: Dict[str, Any] = {
        "amount": int(amount_paise),
        "currency": "INR",
        "receipt": receipt_id[:40],
    }
    if notes:
        payload["notes"] = notes
    try:
        order = client.order.create(payload)
    except Exception as e:
        raise PaymentGatewayError(f"Razorpay order creation failed: {e}")
    return {
        "razorpay_order_id": order["id"],
        "amount_paise": order.get("amount", amount_paise),
        "currency": order.get("currency", "INR"),
        "status": order.get("status", "created"),
    }


def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """Verify a checkout payment signature server-side (HMAC SHA256).

    The order_id MUST come from our own database, never from the client.
    Returns True on success, False on signature mismatch. Raises
    PaymentConfigError when credentials are missing.
    """
    client = _client()
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
        return True
    except Exception as e:
        # The SDK raises SignatureVerificationError on mismatch.
        err_name = type(e).__name__
        if "SignatureVerification" in err_name:
            return False
        raise


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """Verify the X-Razorpay-Signature header of a webhook delivery."""
    import razorpay

    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise PaymentConfigError(
            "RAZORPAY_WEBHOOK_SECRET is not configured."
        )
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID or "", settings.RAZORPAY_KEY_SECRET or ""))
    try:
        client.utility.verify_webhook_signature(
            raw_body.decode("utf-8") if isinstance(raw_body, bytes) else raw_body,
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET,
        )
        return True
    except Exception as e:
        err_name = type(e).__name__
        if "SignatureVerification" in err_name:
            return False
        raise
