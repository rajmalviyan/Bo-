# process_m3u.py
# Bu betik, belirtilen M3U URL'sinden veriyi çeker,
# proxy linklerini temizler ve istenen formata dönüştürür.

import requests
import urllib.parse

# İşlenecek olan M3U dosyasının URL'si
SOURCE_URL = "https://raw.githubusercontent.com/zerodayip/m3u8file/main/rec%2Frecfilm.m3u"
# Çıktı dosyasının adı
OUTPUT_FILE = "recfilm_processed.m3u"
# Kullanılacak olan sabit User-Agent değeri
USER_AGENT = "okhttp/4.12.0"
# Kullanılacak olan sabit Referrer değeri
REFERRER = "https://twitter.com/"

def process_m3u_playlist():
    """
    M3U dosyasını indirir, linkleri işler ve yeni bir dosyaya kaydeder.
    """
    print(f"M3U dosyası indiriliyor: {SOURCE_URL}")
    try:
        # Kaynak URL'den içeriği al
        response = requests.get(SOURCE_URL, timeout=15)
        response.raise_for_status()  # Hata durumunda exception fırlat
        content = response.text
    except requests.exceptions.RequestException as e:
        print(f"Kaynak M3U dosyası indirilirken hata oluştu: {e}")
        return

    lines = content.splitlines()
    processed_lines = []

    # M3U dosyasının başlığını kontrol et ve ekle
    if lines and lines[0].strip() == "#EXTM3U":
        processed_lines.append(lines[0].strip())

    # Satırları döngüye alarak işle
    # Genellikle #EXTINF ve URL satırları çift olarak gelir
    i = 1
    while i < len(lines):
        line = lines[i].strip()

        # Eğer satır bir kanal bilgisi içeriyorsa (#EXTINF)
        if line.startswith("#EXTINF"):
            extinf_line = line

            # Sonraki satırın URL olması beklenir
            i += 1
            if i < len(lines):
                url_line = lines[i].strip()

                # URL'nin proxy formatında olup olmadığını kontrol et
                if "zeroipday-zeroipday.hf.space/proxy/m3u" in url_line:
                    try:
                        # Proxy URL'sini parçalarına ayır
                        parsed_proxy_url = urllib.parse.urlparse(url_line)
                        query_params = urllib.parse.parse_qs(parsed_proxy_url.query)

                        # Sadece 'url' parametresini al
                        actual_url_encoded = query_params.get('url', [None])[0]
                        
                        if actual_url_encoded:
                            # Asıl medya URL'sini decode et
                            actual_url = urllib.parse.unquote(actual_url_encoded)

                            # Önce kanal bilgisini ekle
                            processed_lines.append(extinf_line)

                            # Sabit Referrer ve User-Agent bilgilerini #EXTVLCOPT olarak ekle
                            processed_lines.append(f'#EXTVLCOPT:http-referrer={REFERRER}')
                            processed_lines.append(f'#EXTVLCOPT:http-user-agent={USER_AGENT}')

                            # Son olarak temizlenmiş medya URL'sini ekle
                            processed_lines.append(actual_url)
                        else:
                            # 'url' parametresi bulunamazsa, orijinal satırları koru
                            processed_lines.append(extinf_line)
                            processed_lines.append(url_line)

                    except (KeyError, IndexError, TypeError):
                        # URL parse edilirken bir hata olursa orijinal satırları koru
                        print(f"URL parse edilemedi, orijinal hali korunuyor: {url_line}")
                        processed_lines.append(extinf_line)
                        processed_lines.append(url_line)
                else:
                    # Proxy formatında değilse, satırları olduğu gibi ekle
                    processed_lines.append(extinf_line)
                    processed_lines.append(url_line)
        i += 1

    # İşlenmiş içeriği çıktı dosyasına yaz
    print(f"İşlenmiş M3U dosyası kaydediliyor: {OUTPUT_FILE}")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(processed_lines))
        print("İşlem başarıyla tamamlandı.")
    except IOError as e:
        print(f"Dosyaya yazılırken hata oluştu: {e}")

if __name__ == "__main__":
    process_m3u_playlist()