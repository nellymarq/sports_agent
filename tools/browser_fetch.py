# tools/browser_fetch.py
# Async Playwright browser fetch with global browser and per-call contexts.

import os
import asyncio
from typing import Optional

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

PROFILE_DIR = os.path.join(os.path.dirname(__file__), "browser_profile")

_playwright = None
_browser = None
_browser_lock = asyncio.Lock()


async def _ensure_browser():
    global _playwright, _browser

    async with _browser_lock:
        if _browser is not None:
            return

        os.makedirs(PROFILE_DIR, exist_ok=True)

        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--enable-webgl",
                "--use-gl=desktop",
                "--ignore-certificate-errors",
            ],
        )


async def browser_fetch(url: str, timeout: int = 20000) -> str:
    """
    Async HTML fetch using a shared browser and a fresh context per call.
    """
    await _ensure_browser()

    storage_path = os.path.join(PROFILE_DIR, "storage.json")

    context = await _browser.new_context(
        java_script_enabled=True,
        storage_state=storage_path if os.path.exists(storage_path) else None,
    )
    page = await context.new_page()

    try:
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        html = await page.content()
    except PlaywrightTimeout:
        html = ""
    finally:
        try:
            await context.storage_state(path=storage_path)
        except Exception:
            pass
        await page.close()
        await context.close()

    return html


async def _shutdown():
    global _playwright, _browser
    try:
        if _browser:
            await _browser.close()
        if _playwright:
            await _playwright.stop()
    except Exception:
        pass


def register_shutdown(loop: Optional[asyncio.AbstractEventLoop] = None):
    """
    Optionally call this once at startup to register a clean async shutdown.
    """
    loop = loop or asyncio.get_event_loop()
    loop.create_task(_shutdown())
