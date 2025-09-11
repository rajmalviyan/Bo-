#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cizgivedizi_final.py
--------------------
- ÇizgiVeDizi scraper mantığı + toplu indirme + M3U + Özet Raporu oluşturma.
- Tüm dizileri çeker, her dizi için JSON ve M3U dosyaları oluşturur.
- İşlem sonunda 'output' klasörüne bir özet README.md dosyası yazar.
"""

from __future__ import annotations

import os
import re
import json
import time
from datetime import datetime
import argparse
from dataclasses import dataclass
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": BASE_URL + "/",
}

# =======================
#  Data Classes
# =======================

@dataclass
class Series:
    slug: str; title: str; url: str
    poster: Optional[str] = None; poster_cdn: Optional[str] = None
    plot: Optional[str] = None; tags: Optional[str] = None

@dataclass
class Episode:
    title: str; url: str
    season: Optional[int] = None; episode: Optional[int] = None

@dataclass
class EpisodeLinks:
    url: str
    iframe_src: Optional[str] = None; host: Optional[str] = None

# =======================
#  Scraper Core
# =======================

def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    return s

def _fix_url(u: str) -> str:
    return urljoin(BASE_URL + "/", u)

def get_text_map(path: str, session: requests.Session) -> Dict[str, str]:
    url = _fix_url(path)
    r = session.get(url, timeout=30)
    r.encoding = "utf-8"
    r.raise_for_status()
    text = r.text.replace("\r\n", "\n")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip() and not ln.strip().startswith(("#", "//"))]
    pairs = {}
    for ln in lines:
        parts = re.split(r'[=|:]', ln, 1)
        if len(parts) == 2:
            key, value = parts[0].strip().lstrip('|'), parts[1].strip()
            if key:
                pairs[key] = value
    return pairs

def list_series(session: requests.Session) -> List[Series]:
    isim = get_text_map("/dizi/isim.txt", session)
    poster = get_text_map("/dizi/poster.txt", session)
    plot = get_text_map("/dizi/ozet.txt", session)
    tags = get_text_map("/dizi/etiket.txt", session)
    return [
        Series(
            slug=slug, title=title, url=f"{BASE_URL}/dizi/{slug}/",
            poster=(raw_poster := poster.get(slug)),
            poster_cdn=f"{POSTER_PREPEND}{_fix_url(raw_poster)}" if raw_poster else None,
            plot=plot.get(slug), tags=tags.get(slug)
        ) for slug, title in isim.items()
    ]

def get_episodes(slug: str, session: requests.Session) -> List[Episode]:
    url = f"{BASE_URL}/dizi/{slug}/"
    r = session.get(url, timeout=30); r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    episodes: List[Episode] = []
    for a in soup.select("a.bolum"):
        href = a.get("href", "")
        title_txt = a.select_one(".card-title").get_text(strip=True) if a.select_one(".card-title") else ""
        episodes.append(Episode(
            title=title_txt.split(")", 1)[-1].strip() or title_txt, url=_fix_url(href),
            season=int(s) if (s := a.get("data-sezon")) and s.isdigit() else None,
            episode=int(m.group(1)) if (m := re.search(r"/(\d+)[-.]", href)) else None
        ))
    return episodes

def get_episode_links(episode_url: str, session: requests.Session) -> EpisodeLinks:
    r = session.get(episode_url, timeout=30); r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    iframe = soup.select_one("iframe")
    src = iframe.get("src") if iframe else None
    return EpisodeLinks(url=episode_url, iframe_src=_fix_url(src) if src else None, host=urlparse(src).netloc if src else None)

# =======================
#  Bulk Dumper & M3U/Report Generator
# =======================

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '_', name)

def generate_m3u_for_series(series_data: dict, output_path: str) -> bool:
    content = ["#EXTM3U"]
    for ep in series_data.get("episodes", []):
        if not (src := ep.get("iframe_src")): continue
        s, e, t = ep.get("season"), ep.get("episode"), ep.get("title", "Bölüm")
        prefix = f"S{s:02d}E{e:02d}" if isinstance(s, int) and isinstance(e, int) else f"Bölüm {e or ''}"
        content.append(f"#EXTINF:-1,{prefix.strip()} - {t}")
        content.append(src)
    if len(content) > 1:
        with open(output_path, "w", encoding="utf-8") as f: f.write("\n".join(content))
        return True
    return False

def generate_summary_readme(out_dir: str, stats: dict):
    readme_path = os.path.join(out_dir, "README.md")
    content = [
        f"# ÇizgiVeDizi Arşivi",
        f"**Son Güncelleme:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)",
        f"---",
        f"## İstatistikler",
        f"- **Toplam Dizi Bulundu:** {stats.get('total_series', 0)}",
        f"- **Başarıyla İşlenen Dizi:** {stats.get('processed_series', 0)}",
        f"- **Oluşturulan M3U Dosyası:** {stats.get('m3u_created', 0)}",
        f"- **Hata Alınan Dizi Sayısı:** {stats.get('errors', 0)}",
    ]
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))

def dump_series(slug: str, sess: requests.Session, include_iframe: bool) -> dict:
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
    return {"slug": meta.slug, "title": meta.title, "url": meta.url, "poster": meta.poster,
            "poster_cdn": meta.poster_cdn, "plot": meta.plot, "tags": meta.tags, "episodes": result_eps}

def cmd_dump_all(args):
    out_dir = args.out_dir
    series_dir = os.path.join(out_dir, "series"); os.makedirs(series_dir, exist_ok=True)
    m3u_dir = os.path.join(out_dir, "m3u")
    if args.m3u: os.makedirs(m3u_dir, exist_ok=True)
    
    sess = _make_session()
    slugs = [s.slug for s in list_series(sess)]
    print(f"[i] Toplam {len(slugs)} dizi bulundu. İşlem başlıyor...")
    
    stats = {"total_series": len(slugs), "processed_series": 0, "m3u_created": 0, "errors": 0}
    all_results = []

    def _worker(slug: str):
        try:
            data = dump_series(slug, sess, include_iframe=not args.no_iframe)
            fname = sanitize_filename(slug)
            with open(os.path.join(series_dir, f"{fname}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            m3u_success = False
            if args.m3u:
                m3u_success = generate_m3u_for_series(data, os.path.join(m3u_dir, f"{fname}.m3u"))
            return data, slug, None, m3u_success
        except Exception as e:
            return None, slug, str(e), False

    with ThreadPoolExecutor(max_workers=int(args.workers)) as ex:
        futures = {ex.submit(_worker, slug): slug for slug in slugs}
        for i, future in enumerate(as_completed(futures)):
            data, slug, err, m3u_created = future.result()
            progress = f"[{i + 1}/{len(slugs)}]"
            if err:
                stats['errors'] += 1
                print(f"{progress} [!] Hata ({slug}): {err}")
            else:
                all_results.append(data)
                stats['processed_series'] += 1
                if m3u_created: stats['m3u_created'] += 1
                print(f"{progress} [+] Başarılı: {data['title']}")

    all_results.sort(key=lambda x: x.get('title', ''))
    with open(os.path.join(out_dir, "all.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    generate_summary_readme(out_dir, stats)
    print("\n[+] İşlem tamamlandı. Özet raporu oluşturuldu.")

def main():
    p = argparse.ArgumentParser(description="ÇizgiVeDizi - Toplu JSON, M3U ve Rapor Çıkarıcı")
    p_dump = p.add_subparsers().add_parser("dump-all", help="Tüm veriyi çek ve dosyaları oluştur")
    p_dump.set_defaults(func=cmd_dump_all)
    p_dump.add_argument("--out-dir", default="output", help="Çıktı klasörü")
    p_dump.add_argument("--workers", default="5", help="Eşzamanlı iş parçacığı")
    p_dump.add_argument("--m3u", action="store_true", help="M3U çalma listeleri oluştur")
    p_dump.add_argument("--no-iframe", action="store_true", help="Iframe linklerini çözme (M3U için gerekli)")

    args = p.parse_args()
    if hasattr(args, 'func'):
        if args.m3u and args.no_iframe:
            print("[!] --m3u için iframe çözümlemesi gerekli. --no-iframe yoksayılıyor.")
            args.no_iframe = False
        args.func(args)
    else: p.print_help()

if __name__ == "__main__": main()