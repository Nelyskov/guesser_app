"""
Lamoda parser — Playwright.
Карточки: div[id=SKU][class*='x-product-card__card']
"""

import re
from .base import BaseParser

try:
    from bs4 import BeautifulSoup
    BS4 = True
except ImportError:
    BS4 = False


class LamodaParser(BaseParser):
    SITE        = "Lamoda"
    USE_BROWSER = True

    SEARCH_URL = "https://www.lamoda.ru/catalogsearch/result/?q={query}&page={page}"

    def parse(self, query: str, max_items: int):
        self.log(f"[Lamoda] Поиск: «{query}» max={max_items}", "accent")
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
            self.log(f"[Lamoda] Стр.{page}...", "dim")

            html = self.goto(url, wait="networkidle", timeout=40000)
            if not html:
                self.log("[Lamoda] Страница не загрузилась, стоп", "warn")
                break

            items = self._parse_html(html)
            if not items:
                self.log(f"[Lamoda] Стр.{page}: карточки не найдены, стоп", "warn")
                break

            self.log(f"[Lamoda] Стр.{page}: {len(items)} товаров", "dim")

            for item in items:
                if self.stopped() or collected >= max_items:
                    return
                if not self.price_ok(item["price"]):
                    continue
                yield self.make_product(
                    item["sku"], item["name"], item["price"], item["image"])
                collected += 1

            page += 1

    def _parse_html(self, html: str) -> list:
        if not BS4:
            return []
        soup       = BeautifulSoup(html, "lxml")
        candidates = soup.select("[class*='x-product-card__card']")
        results    = []

        for card in candidates:
            sku = card.get("id", "")
            if not sku or len(sku) < 8:
                continue
            try:
                result = self._parse_card(card, sku)
                if result:
                    results.append(result)
            except Exception:
                pass
        return results

    def _parse_card(self, card, sku: str) -> dict | None:
        # Бренд
        brand_el = card.select_one("[class*='brand']")
        brand    = brand_el.get_text(strip=True) if brand_el else ""

        # Категория (второй текстовый блок)
        texts = [t.strip() for t in card.get_text(separator="\n").split("\n")
                 if t.strip() and "%" not in t and not t.strip()[:3].isdigit()]
        category = ""
        for t in texts:
            if t != brand and len(t) > 2:
                category = t
                break
        name = f"{brand} {category}".strip() if category else brand or sku

        # Убираем цену из названия (например "PUMA 5 990" → "PUMA")
        import re as _re
        name = _re.sub(r'\s+[\d\s]{3,}$', '', name).strip()

        # Цена
        price = 0
        price_new = card.select_one("[class*='price-new']")
        if price_new:
            price = int(re.sub(r"[^\d]", "", price_new.get_text()) or 0)
        if not price:
            all_p = [int(re.sub(r"[^\d]", "", el.get_text()) or 0)
                     for el in card.select("[class*='price']")]
            all_p = [p for p in all_p if p > 0]
            price = min(all_p) if all_p else 0

        # Картинка
        img_el = card.select_one("img[data-src]")
        image  = ""
        if img_el:
            ds    = img_el.get("data-src", "")
            image = ("https:" + ds) if ds.startswith("//") else ds
        if not image:
            img_el2 = card.select_one("img[src*='lmcdn']")
            if img_el2:
                image = img_el2.get("src", "")
        # Playwright подгружает реальные src
        if not image:
            img_el3 = card.select_one("img[src^='http']")
            if img_el3:
                image = img_el3.get("src", "")
        if not image and len(sku) >= 2:
            image = (f"https://a.lmcdn.ru/img600x866"
                     f"/{sku[0]}/{sku[1]}/{sku}_1_v1.jpg")

        if not name or not price:
            return None
        return {"sku": sku, "name": name, "price": price, "image": image}
