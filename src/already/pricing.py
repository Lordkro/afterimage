MISS_USDC = "0.01"
HIT_USDC = "0.002"
SEARCH_USDC = "0.005"

# USDC atomic units (6 decimals) for x402 amounts.
MISS_ATOMIC = "10000"
HIT_ATOMIC = "2000"
SEARCH_ATOMIC = "5000"


def price_usdc(*, cache_hit: bool) -> str:
    return HIT_USDC if cache_hit else MISS_USDC


def price_atomic(*, cache_hit: bool) -> str:
    return HIT_ATOMIC if cache_hit else MISS_ATOMIC
