from __future__ import annotations

from typing import Protocol


class Checkout(Protocol):
    async def create_session(self, *, key_id: str, pack: str, cents: int) -> str: ...


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
