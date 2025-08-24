import asyncio
import aiohttp
import re
import os
from itertools import islice
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
import logging
import time

# --- LOGLAMA AYARLARI ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- TEMEL AYARLAR ---
# BASE_URL artık ana siteyi işaret ediyor, kategori seçimi kullanıcıya bırakıldı.
BASE_URL = "https://dizifun5.com"
# Proxy'ye şimdilik gerek yok, direkt linkler çalışıyor. Gerekirse aktif edilebilir.
# PROXY_BASE_URL = "https://3.nejyoner19.workers.dev/" 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3",
    "Referer": BASE_URL, # Referer eklemek genellikle faydalıdır.
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# --- YARDIMCI FONKSİYONLAR ---

def sanitize_id(text):
    """Metni M3U için geçerli bir TVG ID formatına dönüştürür."""
    if not text:
        return "UNKNOWN"
    turkish_chars = {'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G', 'ı': 'i', 'I': 'I', 'İ': 'I', 'ö': 'o', 'Ö': 'O', 'ş': 's', 'Ş': 'S', 'ü': 'u', 'Ü': 'U'}
    for tr, en in turkish_chars.items():
        text = text.replace(tr, en)
    text = re.sub(r'[^A-Za-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    return text.upper()

def fix_url(url, base=BASE_URL):
    """Kısmi URL'leri tam URL'ye dönüştürür."""
    if not url:
        return None
    return urljoin(base, url)

def hex_to_string(hex_str):
    """Hexadecimal string'i UTF-8 string'e çevirir."""
    try:
        decoded_bytes = bytes.fromhex(hex_str)
        return unquote(decoded_bytes.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as e:
        logger.error(f"[!] Hex çözme hatası: {hex_str} -> {e}")
        return None

async def fetch_page(session, url, timeout=45):
    """Bir web sayfasının içeriğini asenkron olarak alır."""
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            if response.status == 200:
                return await response.text()
            else:
                logger.warning(f"[!] HTTP {response.status} hatası: {url}")
                return None
    except asyncio.TimeoutError:
        logger.error(f"[!] Zaman aşımı hatası ({timeout}s): {url}")
        return None
    except Exception as e:
        logger.error(f"[!] Sayfa getirme hatası ({url}): {e}")
        return None

# --- M3U8 ÇIKARMA MANTIĞI (KOTLIN KODUNDAN UYARLANDI) ---

async def find_playhouse_m3u8(session, file_id):
    """
    Verilen file_id için çalışan bir Playhouse M3U8 URL'si bulur.
    Kotlin kodundaki gibi d1, d2, d3, d4 sunucularını test eder.
    """
    logger.info(f"[*] Playhouse M3U8 aranıyor, File ID: {file_id}")
    domains = ["d1", "d2", "d3", "d4"]
    movie_referer = "https://playhouse.premiumvideo.click/"
    
    for domain in domains:
        m3u8_url = f"https://{domain}.premiumvideo.click/uploads/encode/{file_id}/master.m3u8"
        try:
            # Sadece başlık bilgisi (HEAD) isteği atarak linkin varlığını kontrol etmek daha hızlıdır.
            async with session.head(m3u8_url, headers={"Referer": movie_referer}, timeout=10, allow_redirects=True) as response:
                if response.status == 200:
                    logger.info(f"[+] Çalışan Playhouse M3U8 bulundu: {m3u8_url}")
                    return m3u8_url
        except Exception:
            # Hata durumunda bir sonraki domain'i dene
            logger.debug(f"[-] {domain} domain testi başarısız.")
            continue
            
    logger.warning(f"[!] Playhouse için çalışan M3U8 URL bulunamadı, File ID: {file_id}")
    return None

async def extract_gujan_m3u8(session, gujan_iframe_url):
    """Gujan iframe'inden M3U8 URL'sini çıkarır."""
    logger.info(f"[*] Gujan iframe işleniyor: {gujan_iframe_url}")
    content = await fetch_page(session, gujan_iframe_url)
    if not content:
        return None

    # M3U8 linkini doğrudan script veya source etiketinden ara
    m3u8_match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8)["\']', content) or \
                 re.search(r'<source\s+src=["\'](https?://[^"\']+\.m3u8)["\']', content)
    
    if m3u8_match:
        m3u8_url = m3u8_match.group(1)
        logger.info(f"[+] Gujan'dan M3U8 bulundu: {m3u8_url}")
        return m3u8_url
        
    logger.warning(f"[!] Gujan iframe içinde M3U8 URL bulunamadı.")
    return None

async def get_m3u8_from_episode(session, episode_url):
    """
    Bir bölüm sayfasından M3U8 linkini çıkarır.
    Kotlin kodundaki mantıkla güncellenmiştir.
    """
    content = await fetch_page(session, episode_url)
    if not content:
        return None

    # 1. Yöntem: Script'ler içindeki şifreli (hex) linkleri çözme
    hex_pattern = re.compile(r'hexToString\w*\("([a-fA-F0-9]+)"\)')
    script_tags = re.findall(r'<script.*?>(.*?)</script>', content, re.DOTALL)
    
    for script_content in script_tags:
        hex_matches = hex_pattern.findall(script_content)
        for hex_value in hex_matches:
            decoded_url = hex_to_string(hex_value)
            if not decoded_url:
                continue
            
            normalized_url = fix_url(decoded_url)
            logger.info(f"[*] Çözülen URL işleniyor: {normalized_url}")

            if "playhouse.premiumvideo.click" in normalized_url:
                file_id_match = re.search(r'/player/([a-zA-Z0-9]+)', normalized_url)
                if file_id_match:
                    return await find_playhouse_m3u8(session, file_id_match.group(1))
            
            elif "gujan.premiumvideo.click" in normalized_url:
                return await extract_gujan_m3u8(session, normalized_url)

    # 2. Yöntem: Doğrudan iframe'leri arama (fallback)
    iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', content)
    if iframe_match:
        iframe_url = fix_url(iframe_match.group(1))
        logger.info(f"[*] Fallback: Iframe bulundu: {iframe_url}")
        if "playhouse.premiumvideo.click" in iframe_url:
            file_id_match = re.search(r'/player/([a-zA-Z0-9]+)', iframe_url)
            if file_id_match:
                return await find_playhouse_m3u8(session, file_id_match.group(1))
        elif "gujan.premiumvideo.click" in iframe_url:
            return await extract_gujan_m3u8(session, iframe_url)

    logger.error(f"[!] Bu bölüm için M3U8 linki bulunamadı: {episode_url}")
    return None

# --- SİTE TARAMA FONKSİYONLARI ---

async def get_content_from_page(session, category_url, page_num):
    """Belirli bir kategorinin belirli bir sayfasından içerik listesini alır."""
    page_url = f"{category_url}?p={page_num}"
    logger.info(f"Sayfa {page_num} alınıyor: {page_url}")

    content = await fetch_page(session, page_url)
    if not content:
        return [], False

    soup = BeautifulSoup(content, 'html.parser')
    content_links = []
    # Hem dizi hem film linklerini alacak şekilde seçiciyi genelleştir
    link_elements = soup.select("div.uk-width-1-3 a.uk-position-cover")

    for element in link_elements:
        href = element.get("href")
        if href and ('/dizi/' in href or '/film/' in href):
            full_url = fix_url(href)
            if full_url and full_url not in content_links:
                content_links.append(full_url)

    has_next_page = bool(soup.select_one(".uk-pagination-next:not(.uk-disabled)"))
    logger.info(f"[+] Sayfa {page_num}: {len(content_links)} içerik linki bulundu. Sonraki sayfa: {'Var' if has_next_page else 'Yok'}")
    return content_links, has_next_page

async def get_all_content_from_category(category_url):
    """Bir kategorideki tüm içeriklerin linklerini toplar."""
    async with aiohttp.ClientSession() as session:
        all_content_links = []
        page_num = 1
        while True:
            content_links, has_next_page = await get_content_from_page(session, category_url, page_num)
            if not content_links:
                break
            
            all_content_links.extend(link for link in content_links if link not in all_content_links)
            
            if not has_next_page:
                break
            page_num += 1
            await asyncio.sleep(0.5)

        logger.info(f"[✓] Toplam {len(all_content_links)} benzersiz içerik linki toplandı.")
        return all_content_links

async def get_metadata_and_episodes(session, content_url):
    """Bir içerik (dizi/film) sayfasından meta verileri ve bölüm/film linklerini alır."""
    content = await fetch_page(session, content_url)
    if not content:
        return None, None, []

    soup = BeautifulSoup(content, 'html.parser')
    title = soup.select_one("h1.text-bold").get_text(strip=True) if soup.select_one("h1.text-bold") else "Bilinmeyen Başlık"
    logo_url = fix_url(soup.select_one("img.responsive-img").get("src")) if soup.select_one("img.responsive-img") else ""
    
    episodes = []
    # Film ise, kendi URL'sini tek bölüm olarak döndür
    if '/film/' in content_url:
        episodes.append({'url': content_url, 'season': 1, 'episode': 1, 'name': title})
    # Dizi ise, sezon ve bölümleri ayrıştır
    else:
        season_containers = soup.select("div.season-detail")
        for season_div in season_containers:
            season_id = season_div.get("id", "season-1")
            season_num = int(re.search(r'\d+', season_id).group(0))
            
            episode_elements = season_div.select("div.bolumtitle a")
            for idx, ep_element in enumerate(episode_elements, 1):
                href = ep_element.get("href")
                if href:
                    full_url = f"{content_url.split('?')[0]}{href}" if href.startswith("?") else fix_url(href)
                    ep_name = ep_element.get_text(strip=True)
                    episodes.append({'url': full_url, 'season': season_num, 'episode': idx, 'name': ep_name})
                    
    logger.info(f"[+] '{title}' için {len(episodes)} bölüm/film bulundu.")
    return title, logo_url, episodes

# --- ANA İŞLEM FONKSİYONU ---

async def process_content_list(content_urls, output_filename):
    """Verilen içerik listesini işleyip M3U dosyasına yazar."""
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10)) as session:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")

            for content_url in content_urls:
                try:
                    title, logo_url, episodes = await get_metadata_and_episodes(session, content_url)
                    if not title: continue
                    
                    logger.info(f"\n[+] İşleniyor: {title}")
                    
                    for ep_info in episodes:
                        m3u8_url = await get_m3u8_from_episode(session, ep_info['url'])
                        if not m3u8_url:
                            logger.warning(f"[!] M3U8 bulunamadı: S{ep_info['season']} B{ep_info['episode']} - {ep_info['name']}")
                            continue
                        
                        display_name = f"{title} S{ep_info['season']:02d}E{ep_info['episode']:02d}" if '/dizi/' in content_url else title
                        tvg_id = sanitize_id(display_name)
                        
                        f.write(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{display_name}" tvg-logo="{logo_url}" group-title="{title}",{display_name}\n')
                        f.write(m3u8_url.strip() + "\n")
                        logger.info(f"[✓] Eklendi: {display_name}")
                        
                except Exception as e:
                    logger.error(f"[!!!] İçerik işleme hatası: {content_url} -> {e}", exc_info=True)
                    continue

    logger.info(f"\n[✓✓✓] {output_filename} dosyası başarıyla oluşturuldu.")

def get_category_choice():
    """Kullanıcıdan hangi kategoriyi taramak istediğini alır."""
    categories = {
        "1": ("Diziler", "/diziler"),
        "2": ("Filmler", "/filmler"),
        "3": ("Netflix", "/netflix"),
        "4": ("Exxen", "/exxen"),
        "5": ("Disney+", "/disney"),
        "6": ("BluTV", "/blutv"),
        "7": ("Tüm Diziler (Uzun Sürebilir)", "/diziler"),
    }
    print("Lütfen taramak istediğiniz kategoriyi seçin:")
    for key, (name, _) in categories.items():
        print(f"  {key}) {name}")
    
    while True:
        choice = input("Seçiminiz (1-7): ")
        if choice in categories:
            name, path = categories[choice]
            print(f"'{name}' kategorisi seçildi.")
            return f"{BASE_URL}{path}"
        else:
            print("Geçersiz seçim, lütfen tekrar deneyin.")

async def main():
    start_time = time.time()
    
    category_url = get_category_choice()
    output_file = f"{category_url.split('/')[-1]}.m3u"
    
    content_urls = await get_all_content_from_category(category_url)
    if not content_urls:
        logger.error("[!] Hiç içerik linki bulunamadı. Site yapısı değişmiş olabilir.")
        return

    await process_content_list(content_urls, output_file)

    end_time = time.time()
    logger.info(f"\n[✓] Tüm işlemler tamamlandı. Toplam süre: {end_time - start_time:.2f} saniye")

if __name__ == "__main__":
    asyncio.run(main())
