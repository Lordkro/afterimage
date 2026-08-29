#!/usr/bin/env python3
"""Seed AfterImage by calling GET /v1/page for a list of public URLs."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
DEFAULT_URLS = ROOT / "seed_urls.txt"
DEFAULT_HOST = "https://afterimage.page"


def load_urls(path: Path) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line in seen:
            continue
        seen.add(line)
        urls.append(line)
    return urls


def _headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


async def snapshot(
    client: httpx.AsyncClient,
    host: str,
    url: str,
    sem: asyncio.Semaphore,
    api_key: str | None,
    max_age_s: int,
) -> tuple[str, str, int | None, bool | None, str | None, int | None]:
    async with sem:
        try:
            response = await client.get(
                f"{host.rstrip('/')}/v1/page",
                params={"url": url, "max_age_s": max_age_s},
                headers=_headers(api_key),
            )
        except httpx.HTTPError as exc:
            return url, f"error:{type(exc).__name__}", None, None, None, None
        if response.status_code != 200:
            return url, f"http:{response.status_code}", None, None, None, None
        body = response.json()
        text = body.get("text") or ""
        stored = body.get("stored")
        return (
            url,
            str(body.get("cache")),
            body.get("status"),
            stored if isinstance(stored, bool) else None,
            body.get("stored_reason"),
            len(text) if isinstance(text, str) else None,
        )


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--urls", type=Path, default=DEFAULT_URLS)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument(
        "--api-key",
        default=os.environ.get("AFTERIMAGE_API_KEY"),
        help="Bearer key (or AFTERIMAGE_API_KEY). Required when billing is on.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force live fetches (max_age_s=0) to rewrite stored extracts.",
    )
    args = parser.parse_args()
    urls = load_urls(args.urls)
    if not urls:
        print("no urls", file=sys.stderr)
        return 1
    print(f"seeding {len(urls)} urls via {args.host}", flush=True)
    sem = asyncio.Semaphore(max(1, args.concurrency))
    timeout = httpx.Timeout(45.0, connect=10.0)
    ok = 0
    stored = 0
    stopped = False
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        max_age_s = 0 if args.refresh else 10 * 24 * 60 * 60
        tasks = [
            asyncio.create_task(
                snapshot(client, args.host, url, sem, args.api_key, max_age_s)
            )
            for url in urls
        ]
        for coro in asyncio.as_completed(tasks):
            try:
                url, cache, status, was_stored, reason, chars = await coro
            except asyncio.CancelledError:
                continue
            kept = was_stored is True
            if kept:
                ok += 1
                stored += 1
            mark = "ok" if kept else "skip"
            chars_s = "-" if chars is None else str(chars)
            why = reason or ("stored" if kept else "")
            print(
                f"{mark:4} {cache:12} {status!s:>4} chars={chars_s:<6} {why:<16} {url}",
                flush=True,
            )
            if cache.startswith("http:402") and not stopped:
                stopped = True
                print(
                    "out of credits (HTTP 402); stopping so we do not burn the rest",
                    file=sys.stderr,
                    flush=True,
                )
                for task in tasks:
                    task.cancel()
    search = httpx.get(
        f"{args.host.rstrip('/')}/v1/search",
        params={"q": "python"},
        headers=_headers(args.api_key),
        timeout=30.0,
    )
    indexed = search.json().get("indexed") if search.status_code == 200 else "?"
    print(f"done stored_ok={stored}/{len(urls)} indexed={indexed}")
    if stopped:
        return 3
    return 0 if stored else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
