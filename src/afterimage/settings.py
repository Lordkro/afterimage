from pydantic_settings import BaseSettings, SettingsConfigDict

# Base mainnet USDC
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


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
    facilitator_url: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    sqlite_path: str = "data/afterimage.db"
    # Cache, not an archive. These caps keep the Railway volume small.
    max_snapshots: int = 5_000
    max_text_chars: int = 32_000
    snapshot_ttl_s: int = 7 * 24 * 60 * 60
    persist_error_pages: bool = False


def paid_mode(settings: Settings) -> bool:
    return bool(settings.pay_to.strip() or settings.stripe_secret_key.strip())
