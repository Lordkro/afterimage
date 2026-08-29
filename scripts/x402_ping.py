#!/usr/bin/env python3
"""Pay once per AfterImage resource so PayAI can catalog each one.

  python3 -m pip install 'x402[httpx,evm]'
  export EVM_PRIVATE_KEY=0x…   # MetaMask → Account details → Show private key
  python3 scripts/x402_ping.py

Hits /v1/search, /v1/page, and both MCP tools. The x402 client echoes the
bazaar extension from the 402 into the payment payload — without that echo,
PayAI never lists the resource even if settlement succeeds.
"""

from __future__ import annotations

import asyncio
import os
import sys

HOST = os.environ.get("AFTERIMAGE_HOST", "https://afterimage.page").rstrip("/")

GETS = [
    f"{HOST}/v1/search?q=test",
    f"{HOST}/v1/page?url=https://example.com/",
]
MCP_CALLS = [
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "search_pages",
            "arguments": {"q": "test"},
        },
    },
    {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_page",
            "arguments": {"url": "https://example.com/", "max_age_s": 900},
        },
    },
]


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
    failed = 0
    async with x402HttpxClient(client) as http:
        for url in GETS:
            print(f"\nGET {url}")
            response = await http.get(url)
            await response.aread()
            print(f"HTTP {response.status_code}")
            print(response.text[:800])
            try:
                settle = http_client.get_payment_settle_response(
                    lambda name, headers=response.headers: headers.get(name)
                )
                print("settlement", settle)
            except ValueError:
                print("No PAYMENT-RESPONSE header (payment may not have settled).")
            if response.status_code != 200:
                failed += 1
        for body in MCP_CALLS:
            name = body["params"]["name"]
            print(f"\nPOST {HOST}/mcp tools/call {name}")
            response = await http.post(f"{HOST}/mcp", json=body)
            await response.aread()
            print(f"HTTP {response.status_code}")
            print(response.text[:800])
            try:
                settle = http_client.get_payment_settle_response(
                    lambda name, headers=response.headers: headers.get(name)
                )
                print("settlement", settle)
            except ValueError:
                print("No PAYMENT-RESPONSE header (payment may not have settled).")
            if response.status_code != 200:
                failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
