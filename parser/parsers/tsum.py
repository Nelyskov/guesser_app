"""
ЦУМ parser
Парсит HTML каталога. Карточки: a[data-id][href*="/product/"]
Изображения: st-cdn.tsum.com встроены в HTML.
"""

import re
import json
from .base import BaseParser

try:
    from bs4 import BeautifulSoup
    BS4 = True
except ImportError:
    BS4 = False


class TsumParser(BaseParser):
    SITE = "ЦУМ"

    SEARCH_URL = "https://www.tsum.ru/catalog/search/?q={query}&page={page}"
    SEARCH_API = "https://www.tsum.ru/api/catalog/search/?q={query}&page={page}&page_size=60"

    def parse(self, query: str, max_items: int):
        self.log(f"[ЦУМ] Поиск: «{query}» max={max_items}", "accent")
        self.warm_up("https://www.tsum.ru/")

        collected = 0
        page      = 1

        while collected < max_items and not self.stopped():
            # Сначала JSON API
            items = self._try_api(query, page)
            # Фоллбэк — HTML
            if not items:
                items = self._try_html(query, page)

            if not items:
                self.log(f"[ЦУМ] Стр.{page}: товары не найдены, стоп", "warn")
                break

            self.log(f"[ЦУМ] Стр.{page}: {len(items)} товаров", "dim")

            for item in items:
                if self.stopped() or collected >= max_items:
                    return
                if not self.price_ok(item["price"]):
                    continue
                yield self.make_product(
                    item["id"], item["name"], item["price"], item["image"])
                collected += 1

            page += 1
            self.sleep()

    def _try_api(self, query: str, page: int) -> list:
        url  = self.SEARCH_API.format(query=query.replace(" ", "+"), page=page)
        data = self.get_json(url, extra_headers={
            "Referer": "https://www.tsum.ru/",
            "X-Requested-With": "XMLHttpRequest",
        })
        if not data:
            return []
        raw = data if isinstance(data, list) else \
              (data.get("results") or data.get("products") or data.get("items") or [])
        results = []
        for p in raw:
            try:
                ext_id = str(p.get("id") or p.get("sku") or "")
                name   = p.get("name") or p.get("title", "")
                price  = self._parse_price(
                    p.get("price") or p.get("current_price") or 0)
                images = p.get("images") or p.get("photos") or []
                image  = ""
                if images:
                    first = images[0]
                    image = first if isinstance(first, str) else \
                            first.get("url") or first.get("src", "")
                if ext_id and name and price:
                    results.append({"id": ext_id, "name": name,
                                    "price": price, "image": image})
            except Exception:
                pass
        return results

    def _try_html(self, query: str, page: int) -> list:
        url  = self.SEARCH_URL.format(query=query.replace(" ", "+"), page=page)
        html = self.get_html(url, extra_headers={
            "Accept":  "text/html",
            "Referer": "https://www.tsum.ru/",
        })
        if not html:
            return []
        return self._parse_catalog_html(html)

    def _parse_catalog_html(self, html: str) -> list:
        if not BS4:
            return []
        soup     = BeautifulSoup(html, "lxml")
        cards    = soup.select("a[data-id][href*='/product/']")
        cdn_map  = self._build_cdn_map(html)
        results  = []

        for card in cards:
            try:
                data_id = card.get("data-id", "")
                href    = card.get("href", "")
                sku_m   = re.search(r"/product/(\d+)-", href)
                ext_id  = sku_m.group(1) if sku_m else data_id
                if not ext_id:
                    continue

                name_el = card.select_one("[class*='Top__bodyTop']")
                name    = name_el.get_text(strip=True) if name_el else \
                          card.get_text(separator=" ", strip=True)[:80]

                price_el = card.select_one("[class*='Prices__wrapper']")
                price    = self._parse_price(
                    price_el.get_text()) if price_el else 0
                if not price:
                    for el in card.find_all(True):
                        t = el.string or ""
                        if "₽" in t:
                            price = self._parse_price(t)
                            if price:
                                break

                image = cdn_map.get(data_id, "")
                if not image:
                    img = card.select_one("img[src*='st-cdn']")
                    if img:
                        image = img.get("src", "")

                if name and price:
                    results.append({"id": ext_id, "name": name,
                                    "price": price, "image": image})
            except Exception:
                pass
        return results

    def _build_cdn_map(self, html: str) -> dict:
        cdn_urls = re.findall(
            r'https://st-cdn\.tsum\.com/sig/[a-f0-9]+/width/(?:763|400)/i/'
            r'[0-9a-f/]+/[0-9a-f-]{36}\.jpg', html)
        data_ids = re.findall(r'data-id="(\d+)"', html)
        cdn_map: dict[str, str] = {}
        for i, did in enumerate(data_ids):
            if did not in cdn_map and i < len(cdn_urls):
                cdn_map[did] = cdn_urls[i]
        return cdn_map

    @staticmethod
    def _parse_price(raw) -> int:
        if isinstance(raw, (int, float)):
            return int(raw)
        return int(re.sub(r"[^\d]", "", str(raw)) or 0)
