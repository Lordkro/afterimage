from __future__ import annotations

import base64
import json
from typing import Any, Protocol

from fastapi import Request
from fastapi.responses import JSONResponse

from afterimage.keys import KeyStore
from afterimage.mcp import GET_PAGE_SCHEMA, SEARCH_PAGES_SCHEMA
from afterimage.settings import (
    USDC_EIP712_NAME,
    USDC_EIP712_VERSION,
    Settings,
    paid_mode,
)


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


def _http_get_bazaar(
    *,
    query_example: dict[str, str],
    query_properties: dict[str, dict],
    required_query: list[str],
    output_example: dict[str, Any],
) -> dict[str, Any]:
    return {
        "info": {
            "input": {
                "type": "http",
                "method": "GET",
                "queryParams": query_example,
            },
            "output": {"type": "json", "example": output_example},
        },
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "input": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "const": "http"},
                        "method": {
                            "type": "string",
                            "enum": ["GET", "HEAD", "DELETE"],
                        },
                        "queryParams": {
                            "type": "object",
                            "properties": query_properties,
                            "required": required_query,
                        },
                    },
                    "required": ["type", "method"],
                    "additionalProperties": False,
                },
                "output": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "example": {"type": "object"},
                    },
                },
            },
            "required": ["input"],
        },
    }


def _mcp_bazaar(tool_name: str) -> dict[str, Any]:
    if tool_name == "search_pages":
        schema = SEARCH_PAGES_SCHEMA
        example = {"q": "fastapi background tasks", "limit": 10}
        description = "Search pages already stored in AfterImage. Does not visit the live web."
        output = {
            "q": "fastapi background tasks",
            "indexed": 3,
            "hits": [
                {
                    "url": "https://fastapi.tiangolo.com/",
                    "title": "FastAPI",
                    "snippet": "background tasks",
                }
            ],
        }
    else:
        tool_name = "get_page"
        schema = GET_PAGE_SCHEMA
        example = {"url": "https://example.com/", "max_age_s": 900}
        description = (
            "Return readable text for a public http(s) URL. Reuses a stored copy "
            "if it is newer than max_age_s."
        )
        output = {
            "url": "https://example.com/",
            "text": "Example Domain",
            "hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "cache": "hit",
        }
    return {
        "info": {
            "input": {
                "type": "mcp",
                "toolName": tool_name,
                "description": description,
                "transport": "streamable-http",
                "inputSchema": schema,
                "example": example,
            },
            "output": {"type": "json", "example": output},
        },
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "input": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "const": "mcp"},
                        "toolName": {"type": "string"},
                        "description": {"type": "string"},
                        "transport": {"type": "string"},
                        "inputSchema": {"type": "object"},
                        "example": {"type": "object"},
                    },
                    "required": ["type", "toolName"],
                },
                "output": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "example": {"type": "object"},
                    },
                },
            },
            "required": ["input"],
        },
    }


def bazaar_extension(
    resource_path: str, *, tool_name: str | None = None
) -> dict[str, Any]:
    if tool_name or resource_path.startswith("/mcp"):
        return {"bazaar": _mcp_bazaar(tool_name or "get_page")}
    if resource_path.rstrip("/").endswith("/v1/search"):
        return {
            "bazaar": _http_get_bazaar(
                query_example={"q": "fastapi background tasks", "limit": "10"},
                query_properties={
                    "q": {
                        "type": "string",
                        "description": "Words to find in stored titles and text",
                    },
                    "limit": {
                        "type": "string",
                        "description": "Max hits, 1-50",
                    },
                    "max_age_s": {
                        "type": "string",
                        "description": "Only copies this many seconds old",
                    },
                },
                required_query=["q"],
                output_example={
                    "q": "fastapi background tasks",
                    "indexed": 3,
                    "hits": [
                        {
                            "url": "https://fastapi.tiangolo.com/",
                            "title": "FastAPI",
                            "snippet": "background tasks",
                        }
                    ],
                },
            )
        }
    return {
        "bazaar": _http_get_bazaar(
            query_example={"url": "https://example.com/", "max_age_s": "900"},
            query_properties={
                "url": {
                    "type": "string",
                    "description": "Public http(s) URL to snapshot",
                },
                "max_age_s": {
                    "type": "string",
                    "description": "Reuse a stored copy no older than this many seconds",
                },
            },
            required_query=["url"],
            output_example={
                "url": "https://example.com/",
                "text": "Example Domain",
                "hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "cache": "hit",
                "fetched_at": "2026-08-28T00:00:00Z",
            },
        )
    }


def payment_required(
    *,
    settings: Settings,
    resource_url: str,
    amount: str,
    description: str = "Reusable web snapshot with provenance",
    error: str = "PAYMENT-SIGNATURE header is required",
    resource_path: str = "/v1/page",
    tool_name: str | None = None,
) -> dict[str, Any]:
    return {
        "x402Version": 2,
        "error": error,
        "resource": {
            "url": resource_url,
            "description": description,
            "mimeType": "application/json",
            "serviceName": "AfterImage",
            "tags": ["web", "cache", "search", "snapshot"],
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": settings.network,
                "amount": amount,
                "asset": settings.usdc_asset,
                "payTo": settings.pay_to,
                "maxTimeoutSeconds": 60,
                "extra": {
                    "name": USDC_EIP712_NAME,
                    "version": USDC_EIP712_VERSION,
                },
            }
        ],
        "extensions": bazaar_extension(resource_path, tool_name=tool_name),
    }


def challenge_response(required: dict) -> JSONResponse:
    return JSONResponse(
        status_code=402,
        content=required,
        headers={"PAYMENT-REQUIRED": b64json_encode(required)},
    )


def settlement_headers(result: dict) -> dict[str, str]:
    return {"PAYMENT-RESPONSE": b64json_encode(result)}


def billed_headers(payment: dict | None) -> dict[str, str]:
    if not payment:
        return {}
    headers: dict[str, str] = {}
    if payment.get("rail") != "stripe":
        headers.update(settlement_headers(payment))
    remaining = payment.get("credits_remaining")
    if remaining is not None:
        headers["X-Credits-Remaining"] = f"{float(remaining):.6f}".rstrip("0").rstrip(".")
    return headers


def _bearer_secret(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    api_key = request.headers.get("x-api-key")
    return api_key.strip() if api_key else None


def unpaid_response(
    *,
    settings: Settings,
    resource_path: str,
    amount: str,
    description: str,
    error: str,
    tool_name: str | None = None,
    code: str = "missing_key",
) -> JSONResponse:
    public = settings.public_url.rstrip("/")
    body: dict = {
        "error": error,
        "code": code,
        "checkout": f"POST {public}/v1/billing/checkout",
        "authorization": "Authorization: Bearer ak_live_…",
    }
    if settings.pay_to.strip():
        required = payment_required(
            settings=settings,
            resource_url=f"{public}{resource_path}",
            amount=amount,
            description=description,
            error=error,
            resource_path=resource_path,
            tool_name=tool_name,
        )
        body.update(required)
        return JSONResponse(
            status_code=402,
            content=body,
            headers={"PAYMENT-REQUIRED": b64json_encode(required)},
        )
    return JSONResponse(status_code=402, content=body)


async def require_payment(
    request: Request,
    *,
    settings: Settings,
    facilitator: Facilitator | None,
    amount: str,
    resource_path: str,
    description: str = "Reusable web snapshot with provenance",
    keys: KeyStore | None = None,
    tool_name: str | None = None,
) -> JSONResponse | dict | None:
    """Return a 402 response, or settlement result dict if paid. None if unpaid mode."""
    if not paid_mode(settings):
        return None
    secret = _bearer_secret(request)
    if keys is not None and secret:
        remaining = await keys.balance(secret)
        if remaining is None:
            return unpaid_response(
                settings=settings,
                resource_path=resource_path,
                amount=amount,
                description=description,
                error="Unknown API key.",
                tool_name=tool_name,
                code="unknown_key",
            )
        ok = await keys.debit(secret, int(amount))
        if ok:
            left = await keys.balance(secret)
            return {
                "success": True,
                "rail": "stripe",
                "credits_remaining": (left or 0) / 1_000_000,
            }
        ever = await keys.ever_credited(secret)
        if not ever:
            return unpaid_response(
                settings=settings,
                resource_path=resource_path,
                amount=amount,
                description=description,
                error=(
                    "This key has never been funded. Pay checkout_url from "
                    "POST /v1/billing/checkout."
                ),
                tool_name=tool_name,
                code="unfunded_key",
            )
        return unpaid_response(
            settings=settings,
            resource_path=resource_path,
            amount=amount,
            description=description,
            error="API key is out of credits. POST /v1/billing/checkout to top up.",
            tool_name=tool_name,
            code="insufficient_credits",
        )
    signature = request.headers.get("payment-signature") or request.headers.get(
        "x-payment"
    )
    if signature and settings.pay_to.strip():
        public = settings.public_url.rstrip("/")
        required = payment_required(
            settings=settings,
            resource_url=f"{public}{resource_path}",
            amount=amount,
            description=description,
            resource_path=resource_path,
            tool_name=tool_name,
        )
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
    return unpaid_response(
        settings=settings,
        resource_path=resource_path,
        amount=amount,
        description=description,
        error="Payment required. Buy credits via Stripe checkout or pay with x402.",
        tool_name=tool_name,
        code="missing_key",
    )



