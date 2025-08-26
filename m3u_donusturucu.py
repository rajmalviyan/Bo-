# Gerekli kütüphaneleri içe aktarıyoruz
import requests
import urllib.parse

# Kaynak M3U listesinin URL'si
SOURCE_URL = "https://raw.githubusercontent.com/zerodayip/m3u8file/main/setfilmizle.m3u"

# Dönüştürülmüş listenin kaydedileceği dosya adı
OUTPUT_FILE = "son_liste.m3u"

# Eklenecek olan Referer URL'si
REFERER = "https://vctplay.site/"

def convert_line(line):
    """
    Verilen URL satırını istenen formata dönüştürür.
    URL'den önce #EXTVLCOPT satırını ekler.
    """
    # URL'nin proxy yapısına uyup uymadığını kontrol et
    if "zeroipday-zeroipday.hf.space/proxy/setfilmizle/fastplay?url=" in line:
        try:
            # URL'yi parçalara ayır ve 'url' parametresini al
            parsed_url = urllib.parse.urlparse(line)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            if 'url' not in query_params or not query_params['url']:
                return line
            
            original_video_url = query_params['url'][0]

            # URL'de '/video/' kısmı var mı diye kontrol et
            if '/video/' in original_video_url:
                parts = original_video_url.rsplit('/video/', 1)
                
                if len(parts) == 2:
                    base_url = parts[0]
                    video_id = parts[1]
                    
                    # Yeni URL'yi dinamik video kimliği ile oluştur
                    new_url = f"{base_url}/manifests/{video_id}/master.txt"
                    
                    # Referer bilgisini #EXTVLCOPT formatında oluştur
                    ext_vlc_opt = f"#EXTVLCOPT:http-referrer={REFERER}"
                    
                    # İki satırı birleştirerek döndür
                    return f"{ext_vlc_opt}\n{new_url}"
            
            # Eğer format uygun değilse, dönüşüm yapma
            return line

        except Exception as e:
            print(f"URL dönüştürülürken hata oluştu: {line} -> Hata: {e}")
            return line
    
    # Eğer proxy URL'si değilse, satırı olduğu gibi geri döndür
    return line

def process_m3u():
    """
    Ana M3U işleme fonksiyonu.
    """
    print(f"Kaynak M3U listesi indiriliyor: {SOURCE_URL}")
    
    try:
        response = requests.get(SOURCE_URL, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"M3U listesi indirilemedi: {e}")
        return

    lines = response.text.splitlines()
    new_m3u_content = []

    for line in lines:
        # Eğer satır bir URL ise (genellikle http ile başlar ve # ile başlamaz)
        if line.strip() and not line.strip().startswith("#"):
            converted_line = convert_line(line.strip())
            new_m3u_content.append(converted_line)
        else:
            # Eğer #EXTINF gibi bir metadata satırı ise, olduğu gibi ekle
            new_m3u_content.append(line)
            
    try:
        # Yeni içeriği dosyaya yaz
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            # listeyi \n ile birleştirerek dosyaya yaz
            f.write("\n".join(new_m3u_content))
        print(f"Dönüştürme tamamlandı. Liste '{OUTPUT_FILE}' dosyasına kaydedildi.")
    except IOError as e:
        print(f"Dosya yazılırken bir hata oluştu: {e}")

if __name__ == "__main__":
    process_m3u()