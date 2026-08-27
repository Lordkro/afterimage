from afterimage.settings import Settings


def main() -> None:
    import uvicorn

    settings = Settings()
    uvicorn.run(
        "afterimage.app:app",
        host=settings.host,
        port=settings.port,
        factory=False,
    )
