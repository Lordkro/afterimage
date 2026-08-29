from __future__ import annotations

import httpx


def facilitator_error(prefix: str, response: httpx.Response) -> str:
    text = (response.text or "").strip().replace("\n", " ")[:400]
    if text:
        return f"{prefix} {response.status_code}: {text}"
    return f"{prefix} {response.status_code}"


class HttpFacilitator:
    """x402 facilitator client (verify + settle)."""

    def __init__(self, base_url: str, timeout_s: float = 20.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout_s

    async def settle(self, payload: dict, requirements: dict) -> dict:
        body = {
            "x402Version": requirements.get("x402Version", 2),
            "paymentPayload": payload,
            "paymentRequirements": (requirements.get("accepts") or [None])[0],
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            verify = await client.post(f"{self._base}/verify", json=body)
            if verify.status_code >= 400:
                return {"success": False, "errorReason": facilitator_error("verify", verify)}
            verified = verify.json()
            if verified.get("isValid") is False:
                return {
                    "success": False,
                    "errorReason": verified.get("invalidReason")
                    or verified.get("invalidMessage")
                    or "payment invalid",
                }
            settle = await client.post(f"{self._base}/settle", json=body)
            if settle.status_code >= 400:
                return {"success": False, "errorReason": facilitator_error("settle", settle)}
            result = settle.json()
            return {
                "success": bool(result.get("success", True)),
                "transaction": result.get("transaction") or result.get("txHash") or "",
                "network": result.get("network") or "",
                "payer": result.get("payer") or "",
                "errorReason": result.get("errorReason"),
            }
