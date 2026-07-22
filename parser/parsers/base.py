"""
Base parser — два режима:
  - HTTP (cloudscraper) для ЦУМ
  - Playwright (headless Chrome) для WB, Ozon, Lamoda
"""

import time
import random
import re
from typing import Generator, Callable, Optional
import cloudscraper


class BaseParser:
    SITE      = "unknown"
    USE_BROWSER = False   # переопределяется в подклассах

    def __init__(self,
                 log_fn:    Callable[[str, str], None],
                 stop_fn:   Callable[[], bool],
                 delay:     float = 1.5,
                 min_price: int   = 0,
                 max_price: int   = 0):
        self.log       = log_fn
        self.stopped   = stop_fn
        self.delay     = delay
        self.min_price = min_price
        self.max_price = max_price

        # HTTP scraper (для ЦУМ)
        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self.headers = {
            "User-Agent":      ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/124.0.0.0 Safari/537.36"),
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection":      "keep-alive",
        }

        # Playwright браузер (для WB, Ozon, Lamoda)
        self._pw        = None
        self._browser   = None
        self._context   = None
        self._page      = None

    # ── Playwright ───────────────────────────────────────────────
    def browser_start(self):
        from playwright.sync_api import sync_playwright
        self._pw      = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        self._context = self._browser.new_context(
            locale="ru-RU",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 800},
        )
        self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self._page = self._context.new_page()

    def browser_stop(self):
        try:
            if self._page:    self._page.close()
            if self._context: self._context.close()
            if self._browser: self._browser.close()
            if self._pw:      self._pw.stop()
        except Exception:
            pass

    def goto(self, url: str, wait: str = "domcontentloaded",
             timeout: int = 30000) -> Optional[str]:
        """Переходим на URL, возвращаем HTML или None."""
        try:
            self._page.goto(url, wait_until=wait, timeout=timeout)
            # Даём JS время отрисовать карточки
            time.sleep(random.uniform(2.5, 4.0))
            return self._page.content()
        except Exception as e:
            self.log(f"  browser goto error: {e}", "error")
            return None

    # ── HTTP helpers (для ЦУМ) ───────────────────────────────────
    def get_html(self, url: str, extra_headers: dict | None = None) -> Optional[str]:
        hdrs = {**self.headers, "Accept": "text/html", **(extra_headers or {})}
        try:
            r = self.scraper.get(url, headers=hdrs, timeout=25)
            if r.status_code == 200:
                return r.text
            self.log(f"  HTTP {r.status_code}: {url[:80]}", "warn")
            return None
        except Exception as e:
            self.log(f"  Request error: {e}", "error")
            return None

    def get_json(self, url: str, extra_headers: dict | None = None) -> Optional[dict | list]:
        hdrs = {**self.headers, "Accept": "application/json", **(extra_headers or {})}
        try:
            r = self.scraper.get(url, headers=hdrs, timeout=25)
            if r.status_code == 200:
                return r.json()
            self.log(f"  HTTP {r.status_code}: {url[:80]}", "warn")
            return None
        except Exception as e:
            self.log(f"  JSON error: {e}", "error")
            return None

    def warm_up(self, url: str):
        try:
            self.scraper.get(url, headers={**self.headers, "Accept": "text/html"},
                             timeout=20)
            time.sleep(random.uniform(0.5, 1.0))
        except Exception:
            pass

    def sleep(self):
        jitter = random.uniform(-0.2, 0.4)
        time.sleep(max(0.5, self.delay + jitter))

    # ── price filter ─────────────────────────────────────────────
    def price_ok(self, price: int) -> bool:
        if price <= 0:
            return False
        if self.min_price and price < self.min_price:
            return False
        if self.max_price and price > self.max_price:
            return False
        return True

    def parse(self, query: str, max_items: int) -> Generator[dict, None, None]:
        raise NotImplementedError

    def make_product(self, ext_id: str, name: str,
                     price: int, image_url: str) -> dict:
        return {
            "ext_id":    str(ext_id),
            "site":      self.SITE,
            "name":      name.strip(),
            "price":     int(price),
            "image_url": image_url,
        }
