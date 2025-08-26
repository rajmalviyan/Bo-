# Gerekli kütüphaneleri içe aktarıyoruz
import requests
import urllib.parse
import re

# --- AYARLAR ---

# Kaynak M3U listesinin URL'si
SOURCE_URL = "https://raw.githubusercontent.com/zerodayip/m3u8file/main/setfilmizle.m3u"

# Dönüştürülmüş listenin kaydedileceği dosya adı
OUTPUT_FILE = "son_liste.m3u"

# Eklenecek olan Referer URL'si
REFERER = "https://vctplay.site/"

# Eklenecek olan User-Agent bilgisi
USER_AGENT = "Mozilla/5.0 (Linux; Android 14; 23117RA68G Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Hnlcw/4.0 Chrome/139.0.7258.94 Mobile Safari/536"

# Tüm kanallar için ayarlanacak yeni grup başlığı
NEW_GROUP_TITLE = "Filmler"


def process_url_and_get_headers(line):
    """
    Verilen URL satırını dönüştürür ve başlıklarla birlikte tam bir blok olarak döndürür.
    """
    # URL'nin proxy yapısına uyup uymadığını kontrol et
    if "zeroipday-zeroipday.hf.space/proxy/setfilmizle/fastplay?url=" in line:
        try:
            # URL'yi parçalara ayır ve 'url' parametresini al
            parsed_url = urllib.parse.urlparse(line)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            if 'url' not in query_params or not query_params['url']:
                return line # Dönüşüm yapılamıyorsa orijinal satırı döndür
            
            original_video_url = query_params['url'][0]

            # URL'de '/video/' kısmı var mı diye kontrol et
            if '/video/' in original_video_url:
                parts = original_video_url.rsplit('/video/', 1)
                
                if len(parts) == 2:
                    base_url = parts[0]
                    video_id = parts[1]
                    
                    # Yeni URL'yi dinamik video kimliği ile oluştur
                    new_url = f"{base_url}/manifests/{video_id}/master.txt"
                    
                    # Gerekli başlıkları oluştur
                    ext_referrer = f"#EXTVLCOPT:http-referrer={REFERER}"
                    ext_user_agent = f"#EXTVLCOPT:http-user-agent={USER_AGENT}"
                    
                    # Başlıkları ve yeni URL'yi birleştirerek tam bir blok oluştur
                    return f"{ext_referrer}\n{ext_user_agent}\n{new_url}"
            
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
        # #EXTINF satırını işle
        if line.strip().startswith("#EXTINF"):
            # Regex kullanarak group-title="... " kısmını yenisiyle değiştir
            modified_line = re.sub(
                r'group-title="[^"]*"', 
                f'group-title="{NEW_GROUP_TITLE}"', 
                line
            )
            new_m3u_content.append(modified_line)
        
        # URL satırını işle
        elif line.strip() and not line.strip().startswith("#"):
            # URL'yi dönüştür ve başlıkları ekle
            converted_block = process_url_and_get_headers(line.strip())
            new_m3u_content.append(converted_block)
        
        # Diğer satırları (#EXTM3U gibi) olduğu gibi ekle
        else:
            new_m3u_content.append(line)
            
    try:
        # Yeni içeriği dosyaya yaz
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(new_m3u_content))
        print(f"Dönüştürme tamamlandı. Liste '{OUTPUT_FILE}' dosyasına kaydedildi.")
    except IOError as e:
        print(f"Dosya yazılırken bir hata oluştu: {e}")

if __name__ == "__main__":
    process_m3u()