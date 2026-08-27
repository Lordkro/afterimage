from pydantic_settings import BaseSettings, SettingsConfigDict

# Base mainnet USDC
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ALREADY_", extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    public_url: str = "http://localhost:8080"
    host: str = "0.0.0.0"
    port: int = 8080
    pay_to: str = ""
    network: str = "eip155:8453"
    usdc_asset: str = BASE_USDC
    facilitator_url: str = ""
    sqlite_path: str = "data/already.db"


def paid_mode(settings: Settings) -> bool:
    return bool(settings.pay_to.strip())
