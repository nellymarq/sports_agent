# tools/browser_fetch.py
# Async HTML/JSON fetcher with Playwright support and requests fallback.
# When playwright is unavailable, falls back to aiohttp/requests for
# sites that serve content without JS rendering.

import os
import asyncio
import logging
from typing import Optional

_logger = logging.getLogger("browser_fetch")

# --- Attempt playwright import ---
_HAS_PLAYWRIGHT = False
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    _HAS_PLAYWRIGHT = True
except ImportError:
    _logger.info("Playwright not installed — using requests fallback for browser_fetch")

PROFILE_DIR = os.path.join(os.path.dirname(__file__), "browser_profile")

_playwright = None
_browser = None
_browser_lock = asyncio.Lock()

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
}


# ============================================================
# Playwright-based fetch (preferred when available)
# ============================================================

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


async def _playwright_fetch(url: str, timeout: int = 20000) -> str:
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


# ============================================================
# Requests-based fallback (works for UFCStats, ESPN JSON, etc.)
# ============================================================

async def _requests_fetch(url: str, timeout: int = 15) -> str:
    """Fallback fetch using requests in a thread executor."""
    import requests

    loop = asyncio.get_running_loop()

    def _do_fetch():
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            _logger.warning(f"requests fallback failed for {url}: {e}")
            return ""

    return await loop.run_in_executor(None, _do_fetch)


# ============================================================
# Public API
# ============================================================

async def browser_fetch(url: str, timeout: int = 20000) -> str:
    """
    Async HTML fetch. Uses Playwright if available, otherwise falls back
    to plain HTTP requests (works for non-JS-rendered pages).
    """
    if _HAS_PLAYWRIGHT:
        try:
            return await _playwright_fetch(url, timeout)
        except Exception as e:
            _logger.warning(f"Playwright fetch failed, trying requests fallback: {e}")

    # Fallback: plain requests (timeout in seconds, not ms)
    return await _requests_fetch(url, timeout=max(timeout // 1000, 10))


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
