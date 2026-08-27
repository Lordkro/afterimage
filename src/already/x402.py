from __future__ import annotations

import base64
import json
from typing import Any, Protocol

from fastapi import Request
from fastapi.responses import JSONResponse

from already.settings import Settings


class Facilitator(Protocol):
    async def settle(self, payload: dict, requirements: dict) -> dict: ...


def b64json_encode(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()


def b64json_decode(token: str) -> dict:
    padded = token + "=" * (-len(token) % 4)
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return json.loads(decoder(padded))
        except Exception:
            continue
    raise ValueError("invalid payment payload")


def payment_required(
    *,
    settings: Settings,
    resource_url: str,
    amount: str,
    description: str = "Reusable web snapshot with provenance",
    error: str = "PAYMENT-SIGNATURE header is required",
) -> dict[str, Any]:
    return {
        "x402Version": 2,
        "error": error,
        "resource": {
            "url": resource_url,
            "description": description,
            "mimeType": "application/json",
            "serviceName": "Already",
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": settings.network,
                "amount": amount,
                "asset": settings.usdc_asset,
                "payTo": settings.pay_to,
                "maxTimeoutSeconds": 60,
                "extra": {"name": "USDC", "version": "2"},
            }
        ],
        "extensions": {},
    }


def challenge_response(required: dict) -> JSONResponse:
    return JSONResponse(
        status_code=402,
        content=required,
        headers={"PAYMENT-REQUIRED": b64json_encode(required)},
    )


def settlement_headers(result: dict) -> dict[str, str]:
    return {"PAYMENT-RESPONSE": b64json_encode(result)}


async def require_payment(
    request: Request,
    *,
    settings: Settings,
    facilitator: Facilitator | None,
    amount: str,
    resource_path: str,
    description: str = "Reusable web snapshot with provenance",
) -> JSONResponse | dict | None:
    """Return a 402 response, or settlement result dict if paid. None if unpaid mode."""
    if not settings.pay_to.strip():
        return None
    public = settings.public_url.rstrip("/")
    required = payment_required(
        settings=settings,
        resource_url=f"{public}{resource_path}",
        amount=amount,
        description=description,
    )
    signature = request.headers.get("payment-signature") or request.headers.get(
        "x-payment"
    )
    if not signature:
        return challenge_response(required)
    if facilitator is None:
        required["error"] = "facilitator is not configured"
        return challenge_response(required)
    try:
        payload = b64json_decode(signature)
    except ValueError:
        required["error"] = "PAYMENT-SIGNATURE is not valid JSON"
        return challenge_response(required)
    result = await facilitator.settle(payload, required)
    if not result.get("success"):
        required["error"] = result.get("errorReason") or "payment settlement failed"
        return challenge_response(required)
    return result



