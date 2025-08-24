# Gerekli kütüphaneleri içe aktaralım
import requests
import os
import re # Kategori temizleme işlemi için re modülünü ekledik
from datetime import datetime

# --- YENİ DEĞİŞİKLİK: Hatalı URL düzeltildi ---
# URL'ler öncelik sırasına göre tanımlanmıştır.
# İlk URL'nin içeriği, birleştirilmiş dosyanın en başına eklenecektir.
SOURCE_URLS = [
    "https://raw.githubusercontent.com/ahmet21ahmet/Filmdizi/main/filmler.m3u",
    "https://raw.githubusercontent.com/GitLatte/patr0n/refs/heads/site/lists/power-sinema.m3u" # "patr_n" -> "patr0n" olarak düzeltildi
]

# Çıktı olarak oluşturulacak dosyanın adı
OUTPUT_FILE = "merged_playlist.m3u"
# Hata günlüğü için dosya adı
ERROR_LOG_FILE = "error_log.txt"

def log_error(message):
    """Hataları zaman damgasıyla bir dosyaya kaydeder."""
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()}: {message}\n")

def parse_m3u(content):
    """
    M3U içeriğini ayrıştırır, kategori bilgilerini temizler ve her bir girişi
    (bilgi satırı ve URL) bir demet olarak içeren SIRALI bir liste döndürür.
    Bu fonksiyon, dosyadaki orijinal sıralamayı korur.
    """
    entries = []
    lines = content.strip().split('\n')
    
    if not lines or not lines[0].strip().startswith("#EXTM3U"):
        log_error("Uyarı: M3U dosyası standart #EXTM3U başlığına sahip değil.")
        i = 0
    else:
        i = 1 # Başlığı atla

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            if i + 1 < len(lines) and lines[i+1].strip():
                info_line = line
                
                # Kategori bilgisini (group-title) temizle
                cleaned_info_line = re.sub(r'group-title=".*?"', '', info_line).strip()
                cleaned_info_line = re.sub(r'\s\s+', ' ', cleaned_info_line)
                cleaned_info_line = re.sub(r'\s+,', ',', cleaned_info_line)

                url_line = lines[i+1].strip()
                entries.append((cleaned_info_line, url_line))
                i += 2
            else:
                i += 1
        else:
            i += 1
            
    return entries

def fetch_playlist(url):
    """Verilen URL'den M3U içeriğini çeker."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        log_error(f"URL'den içerik alınamadı: {url} - Hata: {e}")
        return None

def main():
    """Ana betik mantığı."""
    print("M3U listeleri birleştirme işlemi başlatıldı...")
    
    final_playlist_entries = []
    seen_urls = set()

    for url in SOURCE_URLS:
        print(f"İşleniyor (Öncelik sırasına göre): {url}")
        content = fetch_playlist(url)
        
        if content:
            entries = parse_m3u(content)
            print(f"  -> Bu listede {len(entries)} giriş bulundu.")
            
            new_items_from_this_list = 0
            for entry in entries:
                if entry[1] not in seen_urls:
                    final_playlist_entries.append(entry)
                    seen_urls.add(entry[1])
                    new_items_from_this_list += 1
            
            print(f"  -> {new_items_from_this_list} yeni ve benzersiz giriş eklendi.")

    print(f"\nToplam {len(final_playlist_entries)} benzersiz giriş birleştirildi.")

    print(f"Yeni liste dosyası ({OUTPUT_FILE}) yazılıyor...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for entry in final_playlist_entries:
            f.write(f"{entry[0]}\n")
            f.write(f"{entry[1]}\n")

    print("İşlem başarıyla tamamlandı!")

if __name__ == "__main__":
    main()