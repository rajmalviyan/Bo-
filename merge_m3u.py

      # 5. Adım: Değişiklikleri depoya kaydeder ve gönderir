# Gerekli kütüphaneleri içe aktaralım
import requests
import os
from datetime import datetime

# Birleştirilecek M3U listelerinin URL'leri
# Buraya istediğiniz kadar URL ekleyebilirsiniz.
SOURCE_URLS = [
    "https://raw.githubusercontent.com/GitLatte/patr0n/refs/heads/site/lists/power-sinema.m3u",
    "https://raw.githubusercontent.com/ahmet21ahmet/Filmdizi/main/filmler.m3u"
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
    bir demet olarak içeren bir liste döndürür.
    URL'yi anahtar olarak kullanarak yinelenenleri önlemek için bir sözlük kullanır.
    """
    entries = {}
    lines = content.strip().split('\n')
    
    # Dosyanın #EXTM3U ile başlayıp başlamadığını kontrol et
    if not lines or not lines[0].strip().startswith("#EXTM3U"):
        log_error("Uyarı: M3U dosyası standart #EXTM3U başlığına sahip değil.")
        # Yine de işlemeye çalış, başlığı atla
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
                # URL'nin zaten eklenip eklenmediğini kontrol et
                if url_line not in entries:
                    entries[url_line] = (info_line, url_line)
                i += 2 # İki satır atla
            else:
                # Eşleşen URL'si olmayan #EXTINF satırını atla
                i += 1
        else:
            # Geçerli bir giriş değilse atla
            i += 1
            
    # Sözlük değerlerini bir liste olarak döndür
    return list(entries.values())

def fetch_playlist(url):
    """Verilen URL'den M3U içeriğini çeker."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # HTTP hata kodları için (4xx veya 5xx) bir istisna oluşturur
        return response.text
    except requests.exceptions.RequestException as e:
        log_error(f"URL'den içerik alınamadı: {url} - Hata: {e}")
        return None

def main():
    """Ana betik mantığı."""
    print("M3U listeleri birleştirme işlemi başlatıldı...")
    
    all_new_entries_list = []
    for url in SOURCE_URLS:
        print(f"İşleniyor: {url}")
        content = fetch_playlist(url)
        if content:
            all_new_entries_list.extend(parse_m3u(content))

    # URL'ye göre yinelenenleri temizleyelim (farklı listelerde aynı içerik olabilir)
    seen_urls = set()
    unique_new_entries = []
    for entry in all_new_entries_list:
        url = entry[1]
        if url not in seen_urls:
            unique_new_entries.append(entry)
            seen_urls.add(url)

    print(f"Toplam {len(unique_new_entries)} benzersiz giriş bulundu.")

    # Mevcut (eski) birleştirilmiş listeyi oku
    old_entries = []
    if os.path.exists(OUTPUT_FILE):
        print(f"Mevcut liste ({OUTPUT_FILE}) okunuyor...")
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            old_content = f.read()
            old_entries = parse_m3u(old_content)
    else:
        print("Mevcut birleştirilmiş liste bulunamadı. Yeni bir tane oluşturulacak.")

    old_urls = {entry[1] for entry in old_entries}

    # Yeni ve mevcut girişleri ayır
    added_entries = [entry for entry in unique_new_entries if entry[1] not in old_urls]
    existing_entries = [entry for entry in unique_new_entries if entry[1] in old_urls]

    print(f"Tespit edilen yeni giriş sayısı: {len(added_entries)}")
    print(f"Korunan mevcut giriş sayısı: {len(existing_entries)}")

    # Yeni M3U dosyasını yaz
    # Yeni girişler en üste gelecek şekilde sırala
    final_playlist_entries = added_entries + existing_entries

    print(f"Yeni liste dosyası ({OUTPUT_FILE}) yazılıyor...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for entry in final_playlist_entries:
            f.write(f"{entry[0]}\n")
            f.write(f"{entry[1]}\n")

    print("İşlem başarıyla tamamlandı!")

if __name__ == "__main__":
    main()