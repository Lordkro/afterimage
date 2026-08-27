from __future__ import annotations

from typing import Any, Protocol

from afterimage.keys import KeyStore
from afterimage.packs import get_pack


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    getter = getattr(obj, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(obj, key, default)


async def apply_paid_session(keys: KeyStore, session: Any) -> dict[str, Any]:
    status = str(_get(session, "payment_status") or "")
    if status not in {"paid", "no_payment_required"}:
        return {"credited": False, "reason": f"not_paid:{status or 'unknown'}"}
    metadata = _get(session, "metadata") or {}
    pack = get_pack(str(_get(metadata, "pack") or ""))
    key_id = str(_get(metadata, "key_id") or "")
    session_id = str(_get(session, "id") or "")
    if not pack or not key_id or not session_id:
        return {"credited": False, "reason": "missing_metadata"}
    credited = await keys.credit(key_id, pack.micros, session_id)
    return {
        "credited": True,
        "already": not credited,
        "key_id": key_id,
        "pack": pack.id,
        "credits_usd": pack.micros / 1_000_000,
        "session_id": session_id,
    }


class Checkout(Protocol):
    async def create_session(self, *, key_id: str, pack: str, cents: int) -> str: ...

    async def retrieve_session(self, session_id: str) -> Any: ...


class StripeCheckout:
    def __init__(self, *, secret_key: str, public_url: str) -> None:
        import stripe

        self._stripe = stripe
        self._stripe.api_key = secret_key
        self._public = public_url.rstrip("/")

    async def create_session(self, *, key_id: str, pack: str, cents: int) -> str:
        session = self._stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": cents,
                        "product_data": {"name": f"AfterImage credits ({pack})"},
                    },
                    "quantity": 1,
                }
            ],
            success_url=(
                f"{self._public}/v1/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{self._public}/llms.txt",
            metadata={"key_id": key_id, "pack": pack},
        )
        if not session.url:
            raise RuntimeError("Stripe did not return a checkout URL")
        return session.url

    async def retrieve_session(self, session_id: str) -> Any:
        return self._stripe.checkout.Session.retrieve(session_id)
