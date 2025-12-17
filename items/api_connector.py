import requests
from bs4 import BeautifulSoup
from typing import List, Dict


class KurashiruConnector:
    """
    クラシルの検索ページをスクレイピングしてレシピ情報を取得する。
    https://www.kurashiru.com/search?query=豚肉
    """
    def search_recipes(self, keyword: str, limit: int = 10) -> List[Dict]:
        if not keyword:
            return []

        url = "https://www.kurashiru.com/search"
        params = {"query": keyword}
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        recipes: List[Dict] = []

        # 検索結果カード候補をまとめて取得
        result_items = soup.select('a[href^="/recipes/"]') or soup.select('article a')

        for a in result_items[:limit]:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            link = f"https://www.kurashiru.com{href}" if href.startswith("/") else href

            # 画像取得
            img_el = a.select_one("img") or a.select_one("source")
            img = None
            if img_el:
                img = (
                    img_el.get("src")
                    or img_el.get("data-src")
                    or img_el.get("srcset")
                    or img_el.get("data-srcset")
                )

            if title and link:
                recipes.append({
                    "title": title,
                    "url": link,
                    "image_url": img,
                })

        return recipes
