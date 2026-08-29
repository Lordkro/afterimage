from pydantic_settings import BaseSettings, SettingsConfigDict

# Base mainnet USDC. extra.name must match the EIP-712 domain, not the ticker.
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_EIP712_NAME = "USD Coin"
USDC_EIP712_VERSION = "2"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AFTERIMAGE_", extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    public_url: str = "http://localhost:8080"
    host: str = "0.0.0.0"
    port: int = 8080
    pay_to: str = ""
    network: str = "eip155:8453"
    usdc_asset: str = BASE_USDC
    facilitator_url: str = "https://facilitator.payai.network"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    sqlite_path: str = "data/afterimage.db"
    # Cache, not an archive. These caps keep the Railway volume small.
    max_snapshots: int = 5_000
    max_text_chars: int = 100_000
    snapshot_ttl_s: int = 10 * 24 * 60 * 60
    persist_error_pages: bool = False
    removal_email: str = "removal@afterimage.page"

    @property
    def snapshot_ttl_days(self) -> int:
        return max(1, self.snapshot_ttl_s // (24 * 60 * 60))


def paid_mode(settings: Settings) -> bool:
    return bool(settings.pay_to.strip() or settings.stripe_secret_key.strip())
