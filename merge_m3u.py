
# Gerekli kütüphaneleri içe aktaralım
import requests
import os
from datetime import datetime

# --- YENİ: URL'ler artık öncelik sırasına göre tanımlanıyor ---
# Listenin başındaki URL'nin içeriği, birleştirilmiş dosyanın en başına eklenecektir.
# Diğer URL'lerdeki (önceki listelerde bulunmayan) içerikler sırayla sona eklenir.
SOURCE_URLS = [
    "https://raw.githubusercontent.com/ahmet21ahmet/Filmdizi/main/filmler.m3u",
    "https://raw.githubusercontent.com/GitLatte/patr0n/refs/heads/site/lists/power-sinema.m3u"
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
    M3U içeriğini ayrıştırır ve her bir girişi (bilgi satırı ve URL)
    bir demet olarak içeren SIRALI bir liste döndürür.
    Bu fonksiyon, dosyadaki orijinal sıralamayı korur.
    """
    entries = []
    lines = content.strip().split('\n')
    
    # Dosyanın #EXTM3U ile başlayıp başlamadığını kontrol et
    if not lines or not lines[0].strip().startswith("#EXTM3U"):
        log_error("Uyarı: M3U dosyası standart #EXTM3U başlığına sahip değil.")
        i = 0
    else:
        i = 1 # Başlığı atla

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            # Bir sonraki satırın URL olduğunu varsayalım
            if i + 1 < len(lines) and lines[i+1].strip():
                info_line = line
                url_line = lines[i+1].strip()
                entries.append((info_line, url_line))
                i += 2 # İki satır atla
            else:
                # Eşleşen URL'si olmayan #EXTINF satırını atla
                i += 1
        else:
            # Geçerli bir giriş değilse atla
            i += 1
            
    return entries

def fetch_playlist(url):
    """Verilen URL'den M3U içeriğini çeker."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # HTTP hata kodları için bir istisna oluşturur
        return response.text
    except requests.exceptions.RequestException as e:
        log_error(f"URL'den içerik alınamadı: {url} - Hata: {e}")
        return None

def main():
    """Ana betik mantığı."""
    print("M3U listeleri birleştirme işlemi başlatıldı...")
    
    final_playlist_entries = []
    seen_urls = set() # Yinelenen içerikleri engellemek için URL'leri takip eder

    # URL'leri tanımlanan öncelik sırasına göre işle
    for url in SOURCE_URLS:
        print(f"İşleniyor (Öncelik sırasına göre): {url}")
        content = fetch_playlist(url)
        
        if content:
            entries = parse_m3u(content)
            print(f"  -> Bu listede {len(entries)} giriş bulundu.")
            
            new_items_from_this_list = 0
            # Listenin kendi içindeki sırasını koruyarak girişleri işle
            for entry in entries:
                # entry[1] URL'yi içerir
                # Eğer bu URL daha önce eklenmediyse, listeye ekle
                if entry[1] not in seen_urls:
                    final_playlist_entries.append(entry)
                    seen_urls.add(entry[1])
                    new_items_from_this_list += 1
            
            print(f"  -> {new_items_from_this_list} yeni ve benzersiz giriş eklendi.")

    print(f"\nToplam {len(final_playlist_entries)} benzersiz giriş birleştirildi.")

    # Yeni M3U dosyasını yaz
    print(f"Yeni liste dosyası ({OUTPUT_FILE}) yazılıyor...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for entry in final_playlist_entries:
            f.write(f"{entry[0]}\n")
            f.write(f"{entry[1]}\n")

    print("İşlem başarıyla tamamlandı!")

if __name__ == "__main__":
    main()