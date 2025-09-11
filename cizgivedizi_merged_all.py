#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cizgivedizi_merged_all_m3u.py
-----------------------------
- ÇizgiVeDizi scraper mantığı + toplu indirme + M3U oluşturma bir arada.
- Tüm dizileri çeker, klasör içinde her dizi için ayrı JSON ve M3U dosyaları,
  ayrıca toplu bir ALL.json dosyası üretir.

Kullanım örnekleri:
    # Varsayılan çıktı: ./output (sadece JSON)
    python cizgivedizi_merged_all_m3u.py dump-all

    # JSON dosyalarına ek olarak M3U çalma listeleri de oluştur
    python cizgivedizi_merged_all_m3u.py dump-all --m3u

    # Özel klasöre yaz, 4 iş parçacığı kullan ve M3U oluştur
    python cizgivedizi_merged_all_m3u.py dump-all --out-dir C:/temp/cizgi --workers 4 --m3u

Notlar:
- M3U dosyaları `output/m3u/` klasörüne yazılır.
- Çıktılar UTF-8 olarak yazılır.
"""

from __future__ import annotations

import os
import re
import json
import time
import argparse
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

# =======================
#  Configuration
# =======================

BASE_URL = "https://cizgivedizi.com"
POSTER_PREPEND = "https://res.cloudinary.com/abhisheksaha/image/fetch/f_auto/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": BASE_URL + "/",
    "Connection": "close",
}

# =======================
#  Data Classes
# =======================

@dataclass
class Series:
    slug: str
    title: str
    url: str
    poster: Optional[str] = None
    poster_cdn: Optional[str] = None
    plot: Optional[str] = None
    tags: Optional[str] = None

@dataclass
class Episode:
    title: str
    url: str
    season: Optional[int] = None
    episode: Optional[int] = None

@dataclass
class EpisodeLinks:
    url: str
    iframe_src: Optional[str] = None
    host: Optional[str] = None

# =======================
#  Scraper Core
# =======================

def _make_session() -> requests.Session:
    """Creates a new requests session with default headers."""
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    return s

def _fix_url(u: str) -> str:
    """Ensures a URL is absolute."""
    return urljoin(BASE_URL + "/", u)

def _poster_cdn_url(raw: Optional[str]) -> Optional[str]:
    """Generates a Cloudinary CDN URL for a poster."""
    if not raw:
        return None
    absolute = _fix_url(raw)
    return POSTER_PREPEND + absolute

def _smart_split_kv(line: str):
    """Parses a key-value pair from a line in a text file."""
    s = line.strip().lstrip("\ufeff")
    if not s or s.startswith("#") or s.startswith("//"):
        return None
    delimiters = ["=", ":", "|", "\t"]
    for sep in delimiters:
        if sep in s:
            k, v = s.split(sep, 1)
            return k.lstrip("|").strip(), v.strip()
    parts = s.split()
    if len(parts) >= 2:
        return parts[0].lstrip("|"), " ".join(parts[1:]).strip()
    return None

def get_text_map(path: str, session: Optional[requests.Session] = None) -> Dict[str, str]:
    """Fetches a text file from the site and parses it into a dictionary."""
    sess = session or _make_session()
    url = _fix_url(path)
    r = sess.get(url, timeout=20)
    r.encoding = "utf-8"
    r.raise_for_status()
    text = r.text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln for ln in text.split("\n") if ln.strip()]
    pairs = [kv for ln in lines if (kv := _smart_split_kv(ln)) and kv[0] != ""]
    return dict(pairs)

def list_series(session: Optional[requests.Session] = None) -> List[Series]:
    """Lists all available series with their metadata."""
    sess = session or _make_session()
    isim = get_text_map("/dizi/isim.txt", sess)
    poster = get_text_map("/dizi/poster.txt", sess)
    plot = get_text_map("/dizi/ozet.txt", sess)
    tags = get_text_map("/dizi/etiket.txt", sess)

    out: List[Series] = []
    for slug, title in isim.items():
        url = f"{BASE_URL}/dizi/{slug}/"
        raw_poster = poster.get(slug)
        out.append(
            Series(
                slug=slug,
                title=title,
                url=url,
                poster=raw_poster,
                poster_cdn=_poster_cdn_url(raw_poster) if raw_poster else None,
                plot=plot.get(slug),
                tags=tags.get(slug),
            )
        )
    return out

def get_episodes(slug: str, session: Optional[requests.Session] = None) -> List[Episode]:
    """Gets all episodes for a given series slug."""
    sess = session or _make_session()
    url = f"{BASE_URL}/dizi/{slug}/"
    r = sess.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    episodes: List[Episode] = []
    for a in soup.select("a.bolum"):
        href = a.get("href") or ""
        abs_url = _fix_url(href)

        title_el = a.select_one(".card-title")
        title_txt = title_el.get_text(strip=True) if title_el else ""
        title_clean = title_txt.split(")", 1)[-1].strip() or title_txt

        try:
            season = int(a.get("data-sezon", "0"))
        except (ValueError, TypeError):
            season = None

        ep_num = None
        last_seg = urlparse(abs_url).path.rstrip("/").split("/")[-1]
        m = re.search(r"(\d+)", last_seg)
        if m:
            try:
                ep_num = int(m.group(1))
            except (ValueError, TypeError):
                ep_num = None
        
        episodes.append(Episode(title=title_clean or last_seg, url=abs_url, season=season, episode=ep_num))
    return episodes

def get_episode_links(episode_url: str, session: Optional[requests.Session] = None) -> EpisodeLinks:
    """Resolves the iframe source for a single episode URL."""
    sess = session or _make_session()
    url = _fix_url(episode_url)
    r = sess.get(url, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    iframe = soup.select_one("iframe")
    src = iframe.get("src") if iframe else None
    host = urlparse(src).netloc if src else None
    
    return EpisodeLinks(url=url, iframe_src=_fix_url(src) if src else None, host=host)

# =======================
#  Bulk Dumper & M3U Generator
# =======================

def sanitize_filename(name: str) -> str:
    """Removes invalid characters from a string to make it a valid filename."""
    return re.sub(r'[^A-Za-z0-9._-]+', '_', name, flags=re.UNICODE)

def generate_m3u_for_series(series_data: dict, output_path: str):
    """
    Generates an M3U playlist file from the scraped series data.

    Args:
        series_data (dict): The dictionary containing series and episode info.
        output_path (str): The full path to write the .m3u file to.
    """
    if not series_data.get("episodes"):
        return

    m3u_content = ["#EXTM3U"]
    
    for ep in series_data["episodes"]:
        iframe_src = ep.get("iframe_src")
        if not iframe_src:
            continue

        sezon = ep.get("season")
        bolum = ep.get("episode")
        baslik = ep.get("title", "Bilinmeyen Başlık")

        # Smart title formatting for the playlist entry
        prefix = ""
        if isinstance(sezon, int) and isinstance(bolum, int):
            prefix = f"S{sezon:02d}E{bolum:02d} "
        elif isinstance(bolum, int):
            prefix = f"Bölüm {bolum} "
        
        extinf_title = f"{prefix}- {baslik}"

        m3u_content.append(f"#EXTINF:-1,{extinf_title}")
        m3u_content.append(iframe_src)
    
    # Only write the file if it contains at least one valid entry
    if len(m3u_content) > 1:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_content))

def dump_series(slug: str, sess: requests.Session, include_iframe: bool = True) -> dict:
    """Fetches metadata, episodes, and optionally iframe links for a single series."""
    all_meta = {s.slug: s for s in list_series(sess)}
    meta = all_meta.get(slug) or Series(slug=slug, title=slug, url=f"{BASE_URL}/dizi/{slug}/")

    episodes = get_episodes(slug, sess)
    result_eps = []
    for e in episodes:
        ep_dict = {"title": e.title, "url": e.url, "season": e.season, "episode": e.episode}
        if include_iframe:
            try:
                links = get_episode_links(e.url, sess)
                ep_dict.update({"iframe_src": links.iframe_src, "host": links.host})
            except Exception:
                ep_dict.update({"iframe_src": None, "host": None})
        result_eps.append(ep_dict)

    return {
        "slug": meta.slug,
        "title": meta.title,
        "url": meta.url,
        "poster": meta.poster,
        "poster_cdn": meta.poster_cdn,
        "plot": meta.plot,
        "tags": meta.tags,
        "episodes": result_eps,
    }

def cmd_dump_all(args):
    """Main command function to dump all series data."""
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    per_series_dir = os.path.join(out_dir, "series")
    os.makedirs(per_series_dir, exist_ok=True)
    
    m3u_dir = None
    if args.m3u:
        m3u_dir = os.path.join(out_dir, "m3u")
        os.makedirs(m3u_dir, exist_ok=True)

    sess = _make_session()
    all_series = list_series(sess)
    slugs = [s.slug for s in all_series]

    print(f"[i] Toplam dizi bulundu: {len(slugs)}")
    print(f"[i] İş parçacığı sayısı: {args.workers}")
    print(f"[i] Iframe çözme: {'Aktif' if not args.no_iframe else 'Pasif'}")
    print(f"[i] M3U oluşturma: {'Aktif' if args.m3u else 'Pasif'}")

    all_results = []

    def _worker(slug: str):
        try:
            data = dump_series(slug, sess, include_iframe=not args.no_iframe)
            
            # 1. Per-series JSON dosyasını yaz
            fname_json = sanitize_filename(slug) + ".json"
            fpath_json = os.path.join(per_series_dir, fname_json)
            with open(fpath_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 2. (İsteğe bağlı) M3U dosyasını yaz
            if args.m3u and m3u_dir:
                fname_m3u = sanitize_filename(slug) + ".m3u"
                fpath_m3u = os.path.join(m3u_dir, fname_m3u)
                generate_m3u_for_series(data, fpath_m3u)

            return data, slug, None
        except Exception as e:
            return None, slug, str(e)

    with ThreadPoolExecutor(max_workers=max(1, int(args.workers))) as ex:
        futures = {ex.submit(_worker, slug): slug for slug in slugs}
        
        for i, future in enumerate(as_completed(futures)):
            data, slug, err = future.result()
            progress = f"[{i + 1}/{len(slugs)}]"
            if err:
                print(f"{progress} [!] Hata ({slug}): {err}")
            elif data:
                all_results.append(data)
                print(f"{progress} [+] Başarılı: {data['title']}")

    # Toplu all.json dosyasını yaz
    all_path = os.path.join(out_dir, "all.json")
    all_results.sort(key=lambda x: x.get('title', '')) # Başlığa göre sırala
    with open(all_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print("\n[+] İşlem tamamlandı.")
    print(f"[+] Dizi JSON klasörü: {per_series_dir}")
    if args.m3u:
        print(f"[+] Dizi M3U klasörü: {m3u_dir}")
    print(f"[+] Toplu JSON dosyası: {all_path}")

def main():
    p = argparse.ArgumentParser(description="ÇizgiVeDizi - Toplu JSON ve M3U çıkarıcı")
    sub = p.add_subparsers()

    p_dump = sub.add_parser("dump-all", help="Tüm dizileri çek, JSON ve/veya M3U dosyaları oluştur")
    p_dump.add_argument("--out-dir", default="output", help="Çıktı klasörü (varsayılan: ./output)")
    p_dump.add_argument("--workers", default="4", help="Eşzamanlı iş parçacığı sayısı (varsayılan: 4)")
    p_dump.add_argument("--no-iframe", action="store_true", help="İframe linklerini çözme (daha hızlı, M3U için gereklidir)")
    p_dump.add_argument("--m3u", action="store_true", help="JSON dosyalarına ek olarak M3U çalma listeleri oluşturur")
    p_dump.set_defaults(func=cmd_dump_all)

    args = p.parse_args()
    if hasattr(args, 'func'):
        if args.m3u and args.no_iframe:
            print("[!] Uyarı: --m3u seçeneği --no-iframe olmadan çalışmaz. Iframe çözümlemesi aktif ediliyor.")
            args.no_iframe = False
        args.func(args)
    else:
        p.print_help()

if __name__ == "__main__":
    main()