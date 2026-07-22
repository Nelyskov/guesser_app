"""
Wildberries parser — Playwright.
Открывает браузер, вводит запрос в поиск, парсит карточки.
Карточки: article.product-card[data-nm-id]
"""

import re
from .base import BaseParser

try:
    from bs4 import BeautifulSoup
    BS4 = True
except ImportError:
    BS4 = False


class WildberriesParser(BaseParser):
    SITE        = "Wildberries"
    USE_BROWSER = True

    BASE_URL   = "https://www.wildberries.ru"
    SEARCH_URL = "https://www.wildberries.ru/catalog/0/search.aspx?search={query}&page={page}"

    def parse(self, query: str, max_items: int):
        self.log(f"[WB] Поиск: «{query}» max={max_items}", "accent")
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
            self.log(f"[WB] Стр.{page}...", "dim")

            html = self.goto(url, wait="load", timeout=60000)
            if not html:
                self.log("[WB] Страница не загрузилась, стоп", "warn")
                break

            # Ждём появления карточек (до 20 сек)
            try:
                self._page.wait_for_selector(
                    "article.product-card", timeout=20000)
                html = self._page.content()
            except Exception:
                pass

            items = self._parse_html(html)
            if not items:
                self.log(f"[WB] Стр.{page}: карточки не найдены, стоп", "warn")
                break

            self.log(f"[WB] Стр.{page}: {len(items)} товаров", "dim")

            for item in items:
                if self.stopped() or collected >= max_items:
                    return
                if not self.price_ok(item["price"]):
                    self.log(f"  [WB] пропуск по цене: {item['price']}₽", "dim")
                    continue
                yield self.make_product(
                    item["id"], item["name"], item["price"], item["image"])
                collected += 1

            page += 1

    def _parse_html(self, html: str) -> list:
        if not BS4:
            return []
        soup    = BeautifulSoup(html, "lxml")
        cards   = soup.select("article.product-card[data-nm-id]")
        results = []

        for card in cards:
            try:
                nm_id = card.get("data-nm-id", "")
                if not nm_id:
                    continue

                # Бренд
                brand_el = card.select_one(".product-card__brand")
                brand    = brand_el.get_text(strip=True) if brand_el else ""

                # Название
                name_el  = card.select_one(".product-card__name")
                name_raw = name_el.get_text(strip=True).lstrip("/").strip() \
                           if name_el else ""
                name     = f"{brand} {name_raw}".strip() if name_raw else brand

                # Цена — ins без wallet-price
                price = 0
                for ins in card.select("ins.price__lower-price"):
                    if "wallet-price" not in ins.get("class", []):
                        price = int(re.sub(r"[^\d]", "",
                                           ins.get_text()) or 0)
                        break
                if not price:
                    ins = card.select_one("ins.price__lower-price")
                    if ins:
                        price = int(re.sub(r"[^\d]", "",
                                           ins.get_text()) or 0)

                # Картинка
                image = self._build_image_url(int(nm_id))

                if name and price:
                    results.append({"id": nm_id, "name": name,
                                    "price": price, "image": image})
            except Exception:
                pass
        return results

    def _build_image_url(self, nm_id: int) -> str:
        vol  = nm_id // 100000
        part = nm_id // 1000
        b    = self._basket(vol)
        return (f"https://basket-{b:02d}.wbbasket.ru"
                f"/vol{vol}/part{part}/{nm_id}/images/big/1.webp")

    @staticmethod
    def _basket(vol: int) -> int:
        table = [
            (143,1),(287,2),(431,3),(719,4),(1007,5),(1061,6),(1115,7),
            (1169,8),(1313,9),(1601,10),(1655,11),(1919,12),(2045,13),
            (2189,14),(2405,15),(2621,16),(2837,17),(3053,18),(3269,19),
            (3485,20),(3701,21),(3917,22),(4133,23),(4349,24),(4565,25),
            (4781,26),(4997,27),(5213,28),(5429,29),(5645,30),(5861,31),
            (6077,32),(6293,33),(6509,34),(6725,35),(6941,36),(7157,37),
            (7373,38),(7589,39),(7805,40),(8021,41),(8237,42),(8453,43),
            (8669,44),(8885,45),(9101,46),(9317,47),(9533,48),
        ]
        for threshold, num in table:
            if vol <= threshold:
                return num
        return 48 + (vol - 9533) // 216 + 1
