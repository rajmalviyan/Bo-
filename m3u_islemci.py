# Gerekli kütüphaneleri içe aktarıyoruz.
import requests
import re
from urllib.parse import unquote

def find_m3u8_link(url):
    """
    Verilen 'embed' URL'sinin kaynak kodundan asıl .m3u8 linkini bulur.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': url
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text
        
        match = re.search(r'file:"(https?://[^\s"]+?\.m3u8[^"]*)"', html_content)
        if match:
            return unquote(match.group(1))
        
        generic_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*?)', html_content)
        if generic_match:
            return unquote(generic_match.group(0))
            
        return None

    except requests.exceptions.RequestException as e:
        print(f"  [HATA] {url} adresine erişilemedi: {e}")
        return None

def process_m3u_playlist(playlist_url):
    """
    Bir M3U playlist URL'si alır, içindeki linkleri işler ve yeni bir playlist içeriği döndürür.
    """
    print(f"Playlist indiriliyor: {playlist_url}")
    try:
        response = requests.get(playlist_url)
        response.raise_for_status()
        playlist_content = response.text
    except requests.exceptions.RequestException as e:
        print(f"Ana playlist indirilemedi: {e}")
        return None

    lines = playlist_content.splitlines()
    new_playlist_lines = []
    
    for i in range(len(lines)):
        line = lines[i].strip()
        
        if line.startswith("#EXTINF:"):
            new_playlist_lines.append(line)
            
            if i + 1 < len(lines):
                embed_url = lines[i + 1].strip()
                
                if embed_url.startswith("http"):
                    title = line.split(',')[-1]
                    print(f"\nİşleniyor: {title}")
                    print(f"  -> Orijinal link: {embed_url}")
                    
                    stream_link = find_m3u8_link(embed_url)
                    
                    if stream_link:
                        print(f"  => Bulunan link: {stream_link}")
                        new_playlist_lines.append(stream_link)
                    else:
                        print("  !! Asıl link bulunamadı, orijinal link korunuyor.")
                        new_playlist_lines.append(embed_url)
                else:
                    new_playlist_lines.append(lines[i+1])
        
        elif not (i > 0 and lines[i-1].startswith("#EXTINF:")):
             new_playlist_lines.append(line)

    return "\n".join(new_playlist_lines)

if __name__ == "__main__":
    INPUT_PLAYLIST_URL = "https://raw.githubusercontent.com/zerodayip/m3u8file/main/dizigomfilmler.m3u"
    OUTPUT_FILENAME = "dizigom_cozulmus.m3u"

    print("İşlem başlıyor...")
    processed_content = process_m3u_playlist(INPUT_PLAYLIST_URL)

    if processed_content:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(processed_content)
        print(f"\nİşlem tamamlandı! Yeni liste '{OUTPUT_FILENAME}' adıyla kaydedildi.")
    else:
        print("\nİşlem başarısız oldu.")