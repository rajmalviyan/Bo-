import os
import re
import json
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

headers = {
    "User-Agent": "Mozilla/5.0",
}
IMDB_CACHE_FILE = "xtream/imdb_vod.json"
def load_imdb_cache():
    if os.path.exists(IMDB_CACHE_FILE):
        try:
            with open(IMDB_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}
def save_imdb_cache(cache: dict):
    os.makedirs(os.path.dirname(IMDB_CACHE_FILE), exist_ok=True)
    with open(IMDB_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
def get_current_domain():
    url = "https://raw.githubusercontent.com/zerodayip/seriesmovies/refs/heads/main/domain/setfimizle.txt"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    for line in r.text.splitlines():
        line = line.strip()
        if line.startswith("http"):
            return line.rstrip("/")
    return None
def get_embed_links(film_url: str):
    results = []
    with requests.Session() as s:
        resp = s.get(film_url, headers={**headers, "Referer": film_url})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        playex_div = soup.select_one("div#playex")
        nonce = playex_div.get("data-nonce") if playex_div else None
        if not nonce:
            return results
        # Önce FastPlay butonlarını bul
        buttons = [
            btn for btn in soup.select("nav.player a, a.options2")
            if btn.get("data-player-name", "").lower() == "fastplay"
        ]
        player_name = "FastPlay"
        # Eğer FastPlay yoksa SetPlay'e bak
        if not buttons:
            buttons = [
                btn for btn in soup.select("nav.player a, a.options2")
                if btn.get("data-player-name", "").lower() == "setplay"
            ]
            player_name = "SetPlay"
        if not buttons:
            return results
        # Dil fallback
        dil_span = soup.select_one("div.data span.dil")
        fallback_lang = dil_span.get_text(strip=True) if dil_span else "Bilinmiyor"
        for btn in buttons:
            post_id = btn.get("data-post-id")
            part_key = btn.get("data-part-key", "").strip()
            language = part_key if part_key else fallback_lang
            payload = {
                "action": "get_video_url",
                "nonce": nonce,
                "post_id": post_id,
                "player_name": player_name,
                "part_key": part_key,
            }
            ajax_headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": film_url,
                "X-Requested-With": "XMLHttpRequest",
            }
            r = s.post(
                f"{film_url.split('/film/')[0]}/wp-admin/admin-ajax.php",
                data=payload,
                headers=ajax_headers,
            )
            try:
                data = r.json()
            except Exception:
                continue
            embed_url = data.get("data", {}).get("url")
            if embed_url:
                results.append((language, embed_url))
    return results
def fetch_imdb_poster(imdb_id: str):
    imdb_resp = requests.get(f"https://www.imdb.com/title/{imdb_id}/", headers=headers, timeout=15)
    imdb_resp.raise_for_status()
    imdb_soup = BeautifulSoup(imdb_resp.text, "html.parser")
    og_image = imdb_soup.find("meta", property="og:image")
    if og_image:
        return og_image.get("content")
    return None
def get_imdb_id_and_poster(film_name: str, film_url: str):
    film_name_key = film_name.strip().upper()
    cache = load_imdb_cache()
    if film_name_key in cache:
        return cache[film_name_key]["imdb_id"], cache[film_name_key]["poster"]
    resp = requests.get(film_url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    imdb_id = None
    poster_url = None
    imdb_link = soup.select_one("a[href*='imdb.com/title/']")
    if imdb_link:
        match = re.search(r"(tt\d+)", imdb_link["href"])
        if match:
            imdb_id = match.group(1)
            # Cache'de yoksa güncelle
            poster_url = fetch_imdb_poster(imdb_id)
            cache[film_name_key] = {"imdb_id": imdb_id, "poster": poster_url}
            save_imdb_cache(cache)
    return imdb_id, poster_url
def scrape_movies_all_pages(start_page_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(start_page_url, timeout=60000)
        while True:
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            section = soup.find("section", class_="module")
            if not section:
                print("[!] Film bölümü bulunamadı")
            else:
                articles = section.find_all("article", class_="item")
                for article in articles:
                    a_tag = article.find("a", href=True)
                    h2_tag = article.find("h2")
                    if a_tag and h2_tag:
                        name = h2_tag.get_text(strip=True)
                        link = a_tag["href"]
                        imdb_id, poster = get_imdb_id_and_poster(name, link)
                        print(f"\n🎬 {name} -> {link}")
                        if imdb_id:
                            print(f"   📺 IMDb: {imdb_id}")
                        if poster:
                            print(f"   🖼️ Poster: {poster}")
                        embeds = get_embed_links(link)
                        for lang, url in embeds:
                            print(f"   {lang} → {url}")
            # Sonraki sayfa
            next_btn = page.query_selector("span.next-page")
            if next_btn and "disabled" not in next_btn.get_attribute("class"):
                print("[*] Sonraki sayfaya geçiliyor...")
                next_btn.click()
                page.wait_for_timeout(2000)  # 2 saniye bekle
            else:
                print("[*] Son sayfaya ulaşıldı.")
                break
        browser.close()
if __name__ == "__main__":
    domain = get_current_domain()
    if domain:
        start_url = f"{domain}/film/"
        scrape_movies_all_pages(start_url)
    else:
        print("[!] Domain alınamadı")
