import os
import re
import json
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --- AYARLAR ---
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.google.com/"
}
IMDB_CACHE_FILE = "xtream/imdb_vod.json"
M3U_OUTPUT_FILE = "filmler.m3u"

# --- ÖNBELLEK FONKSİYONLARI ---
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

# --- ANA FONKSİYONLAR ---
def get_current_domain():
    """GitHub'dan güncel site domain'ini alır."""
    try:
        url = "https://raw.githubusercontent.com/zerodayip/seriesmovies/refs/heads/main/domain/setfimizle.txt"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        for line in r.text.splitlines():
            line = line.strip()
            if line.startswith("http"):
                return line.rstrip("/")
    except requests.RequestException as e:
        print(f"[!] Domain alınırken hata oluştu: {e}")
        return None

def get_m3u8_from_embed(embed_url: str):
    """Verilen embed URL'sinden .m3u8 linkini ayıklar."""
    if not embed_url:
        return None
    try:
        # Bazı embed linkleri // ile başlayabilir, https: ekliyoruz
        if embed_url.startswith("//"):
            embed_url = "https:" + embed_url

        r = requests.get(embed_url, headers={**headers, "Referer": embed_url}, timeout=15)
        r.raise_for_status()
        
        # M3U8 linkini bulmak için Regex kullanıyoruz. Genellikle 'file:' veya 'sources:' içinde olur.
        # Örnek: file:"https://.../video.m3u8"
        match = re.search(r'file\s*:\s*["\'](https?://[^\'"]+\.m3u8)["\']', r.text)
        if match:
            return match.group(1)
            
        # Alternatif kalıp
        match = re.search(r'["\'](https?://[^\'"]+\.m3u8)["\']', r.text)
        if match:
            return match.group(1)

    except requests.RequestException as e:
        print(f"   [!] M3U8 alınırken hata: {embed_url} - {e}")
    except Exception as e:
        print(f"   [!] Beklenmedik hata (get_m3u8_from_embed): {e}")
        
    return None

def get_embed_links(film_url: str):
    """Film sayfasından FastPlay/SetPlay embed linklerini alır."""
    results = []
    try:
        with requests.Session() as s:
            resp = s.get(film_url, headers={**headers, "Referer": film_url})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            playex_div = soup.select_one("div#playex")
            nonce = playex_div.get("data-nonce") if playex_div else None
            if not nonce:
                return results

            buttons = [btn for btn in soup.select("nav.player a, a.options2") if btn.get("data-player-name", "").lower() in ["fastplay", "setplay"]]
            if not buttons:
                return results

            dil_span = soup.select_one("div.data span.dil")
            fallback_lang = dil_span.get_text(strip=True) if dil_span else "Bilinmiyor"

            for btn in buttons:
                post_id = btn.get("data-post-id")
                player_name = btn.get("data-player-name")
                part_key = btn.get("data-part-key", "").strip()
                language = part_key if part_key else fallback_lang
                
                payload = {"action": "get_video_url", "nonce": nonce, "post_id": post_id, "player_name": player_name, "part_key": part_key}
                ajax_url = f"{film_url.split('/film/')[0]}/wp-admin/admin-ajax.php"
                ajax_headers = {"User-Agent": "Mozilla/5.0", "Referer": film_url, "X-Requested-With": "XMLHttpRequest"}
                
                r = s.post(ajax_url, data=payload, headers=ajax_headers)
                data = r.json()
                embed_url = data.get("data", {}).get("url")
                
                if embed_url:
                    results.append((language, embed_url))
    except Exception as e:
        print(f"[!] Embed linkleri alınırken hata: {e}")
    return results

def fetch_imdb_poster(imdb_id: str):
    """IMDb sayfasından poster URL'sini alır."""
    try:
        imdb_resp = requests.get(f"https://www.imdb.com/title/{imdb_id}/", headers=headers, timeout=15)
        imdb_resp.raise_for_status()
        imdb_soup = BeautifulSoup(imdb_resp.text, "html.parser")
        og_image = imdb_soup.find("meta", property="og:image")
        if og_image:
            return og_image.get("content")
    except requests.RequestException as e:
        print(f"   [!] IMDb posteri alınamadı: {imdb_id} - {e}")
    return None

def get_imdb_id_and_poster(film_name: str, film_url: str):
    """Film adı ve URL'sinden IMDb ID ve posterini bulur."""
    film_name_key = film_name.strip().upper()
    cache = load_imdb_cache()
    if film_name_key in cache:
        return cache[film_name_key]["imdb_id"], cache[film_name_key]["poster"]
    
    try:
        resp = requests.get(film_url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        imdb_link = soup.select_one("a[href*='imdb.com/title/']")
        if imdb_link:
            match = re.search(r"(tt\d+)", imdb_link["href"])
            if match:
                imdb_id = match.group(1)
                poster_url = fetch_imdb_poster(imdb_id)
                cache[film_name_key] = {"imdb_id": imdb_id, "poster": poster_url}
                save_imdb_cache(cache)
                return imdb_id, poster_url
    except requests.RequestException as e:
        print(f"[!] IMDb ID alınırken hata: {film_name} - {e}")
        
    return None, None

def scrape_movies_all_pages(start_page_url):
    """Tüm film sayfalarını gezer ve M3U dosyası oluşturur."""
    # M3U dosyasını başlat
    with open(M3U_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(start_page_url, timeout=60000)
        
        while True:
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            section = soup.find("section", class_="module")
            
            if not section:
                print("[!] Film bölümü bulunamadı.")
                break

            articles = section.find_all("article", class_="item")
            for article in articles:
                a_tag = article.find("a", href=True)
                h2_tag = article.find("h2")
                if not (a_tag and h2_tag):
                    continue

                name = h2_tag.get_text(strip=True)
                link = a_tag["href"]
                
                print(f"\n🎬 Film işleniyor: {name}")
                
                imdb_id, poster = get_imdb_id_and_poster(name, link)
                if imdb_id:
                    print(f"   📺 IMDb: {imdb_id}")
                if poster:
                    print(f"   🖼️ Poster: {poster}")

                embeds = get_embed_links(link)
                if not embeds:
                    print("   [!] Embed link bulunamadı.")
                    continue

                for lang, embed_url in embeds:
                    print(f"   🔗 {lang} Embed: {embed_url}")
                    m3u8_link = get_m3u8_from_embed(embed_url)
                    
                    if m3u8_link:
                        print(f"   ✅ M3U8 Bulundu: {m3u8_link}")
                        # M3U dosyasına yaz
                        with open(M3U_OUTPUT_FILE, "a", encoding="utf-8") as f:
                            # Oynatıcıların bilgileri okuyabilmesi için format
                            extinf_line = f'#EXTINF:-1 tvg-id="{imdb_id}" tvg-logo="{poster}" group-title="Filmler",{name} ({lang})\n'
                            f.write(extinf_line)
                            f.write(m3u8_link + "\n")
                    else:
                        print("   ❌ M3U8 linki bu embed sayfasında bulunamadı.")

            # Sonraki sayfaya geçiş
            next_btn = page.query_selector("span.next-page:not(.disabled)")
            if next_btn:
                print("\n[*] Sonraki sayfaya geçiliyor...")
                next_btn.click()
                page.wait_for_load_state('networkidle', timeout=30000)
            else:
                print("\n[*] Tarama tamamlandı. Son sayfaya ulaşıldı.")
                break
                
        browser.close()

if __name__ == "__main__":
    domain = get_current_domain()
    if domain:
        start_url = f"{domain}/film/"
        print(f"[*] Tarama başlatılıyor: {start_url}")
        scrape_movies_all_pages(start_url)
        print(f"\n[SUCCESS] Tüm filmler '{M3U_OUTPUT_FILE}' dosyasına kaydedildi.")
    else:
        print("[!] Geçerli bir domain alınamadığı için işlem başlatılamadı.")