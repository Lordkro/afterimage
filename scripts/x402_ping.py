#!/usr/bin/env python3
"""Pay once for GET /v1/search so AfterImage can be indexed in the x402 Bazaar.

  python3 -m pip install 'x402[httpx,evm]'
  export EVM_PRIVATE_KEY=0x…   # MetaMask → Account details → Show private key
  python3 scripts/x402_ping.py
"""

from __future__ import annotations

import asyncio
import os
import sys

URL = os.environ.get("AFTERIMAGE_URL", "https://afterimage.page/v1/search?q=test")


async def main() -> int:
    key = (os.environ.get("EVM_PRIVATE_KEY") or "").strip()
    if key.startswith("0x") and len(key) == 42:
        print(
            "That value is a wallet ADDRESS, not a private key. "
            "The address is already public (payTo). The key is 0x plus 64 hex chars.",
            file=sys.stderr,
        )
        print(
            "MetaMask → account → ⋮ → Account details → Show private key "
            "(password) → Hold to reveal. Not the 0x address at the top.",
            file=sys.stderr,
        )
        return 2
    if not key.startswith("0x") or len(key) != 66:
        print(
            "EVM_PRIVATE_KEY must be 0x plus 64 hex characters (66 total).",
            file=sys.stderr,
        )
        print(
            "MetaMask → account → ⋮ → Account details → Show private key.",
            file=sys.stderr,
        )
        return 2

    from eth_account import Account
    from x402 import x402Client
    from x402.http import x402HTTPClient
    from x402.http.clients import x402HttpxClient
    from x402.mechanisms.evm import EthAccountSigner
    from x402.mechanisms.evm.exact.register import register_exact_evm_client

    account = Account.from_key(key)
    client = x402Client().set_spend_controls({"max_amount_per_payment": "$1"})
    register_exact_evm_client(client, EthAccountSigner(account))
    http_client = x402HTTPClient(client)

    print(f"Paying from {account.address}")
    print(f"GET {URL}")

    async with x402HttpxClient(client) as http:
        response = await http.get(URL)
        await response.aread()

    print(f"HTTP {response.status_code}")
    text = response.text
    print(text[:1500])
    try:
        settle = http_client.get_payment_settle_response(
            lambda name: response.headers.get(name)
        )
        print("settlement", settle)
    except ValueError:
        print("No PAYMENT-RESPONSE header (payment may not have settled).")

    return 0 if response.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
