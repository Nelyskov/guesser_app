"""
Ozon parser — Playwright.
Карточки: div[class*='tile-root'][data-index]
"""

import re
from .base import BaseParser

try:
    from bs4 import BeautifulSoup
    BS4 = True
except ImportError:
    BS4 = False


class OzonParser(BaseParser):
    SITE        = "Ozon"
    USE_BROWSER = True

    SEARCH_URL = "https://www.ozon.ru/search/?text={query}&page={page}&from_global=true"

    def parse(self, query: str, max_items: int):
        self.log(f"[Ozon] Поиск: «{query}» max={max_items}", "accent")
        self.browser_start()
        try:
            yield from self._do_parse(query, max_items)
        finally:
            self.browser_stop()

    def _do_parse(self, query: str, max_items: int):
        collected = 0
        page      = 1

        while collected < max_items and not self.stopped():
            url  = self.SEARCH_URL.format(
                query=query.replace(" ", "+"), page=page)
            self.log(f"[Ozon] Стр.{page}...", "dim")

            html = self.goto(url, wait="load", timeout=60000)
            if not html:
                self.log("[Ozon] Страница не загрузилась, стоп", "warn")
                break

            # Ждём карточки и прокручиваем для подгрузки
            try:
                self._page.wait_for_selector(
                    "div[class*='tile-root']", timeout=20000)
                # Прокрутка вниз для lazy load
                self._page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                import time; time.sleep(1.5)
                self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                import time; time.sleep(1.5)
                html = self._page.content()
            except Exception as e:
                self.log(f"[Ozon] Ошибка ожидания: {e}", "warn")
                html = self._page.content()

            items = self._parse_html(html)
            if not items:
                self.log(f"[Ozon] Стр.{page}: карточки не найдены, стоп", "warn")
                break

            self.log(f"[Ozon] Стр.{page}: {len(items)} товаров", "dim")

            for item in items:
                if self.stopped() or collected >= max_items:
                    return
                if not self.price_ok(item["price"]):
                    continue
                yield self.make_product(
                    item["id"], item["name"], item["price"], item["image"])
                collected += 1

            page += 1

    def _parse_html(self, html: str) -> list:
        if not BS4:
            return []
        soup    = BeautifulSoup(html, "lxml")
        cards   = soup.select("div[class*='tile-root'][data-index]")
        results = []

        for card in cards:
            try:
                # ID из ссылки
                link = card.select_one("a[href*='/product/']")
                if not link:
                    continue
                m = re.search(r'/product/[^/]+-(\d+)/', link.get("href", ""))
                if not m:
                    continue
                prod_id = m.group(1)

                # Название
                name_links = card.select("a[href*='/product/']")
                name = ""
                for nl in name_links:
                    t = nl.get_text(strip=True)
                    if t and len(t) > 3:
                        name = t
                        break

                # Бренд
                brand = ""
                for bd in card.select("div[class*='c7w1']"):
                    spans = bd.select("span[class*='tsBodyControl400Small']")
                    if spans:
                        brand = spans[0].get_text(strip=True)
                        break
                full_name = f"{brand} {name}".strip() if brand else name

                # Цена
                price_el = card.select_one("span[class*='tsHeadline500Medium']")
                price    = int(re.sub(r"[^\d]", "",
                               price_el.get_text()) or 0) if price_el else 0

                # Картинка
                image = ""
                for img in card.select("img"):
                    srcset = img.get("srcset", "")
                    if "ozone.ru" in srcset or "ozonusercontent" in srcset:
                        image = srcset.split(",")[0].strip().split(" ")[0]
                        break
                    src = img.get("src", "")
                    if src.startswith("http") and ("ozone" in src or "cdn" in src):
                        image = src
                        break

                if full_name and price:
                    results.append({"id": prod_id, "name": full_name,
                                    "price": price, "image": image})
            except Exception:
                pass
        return results
