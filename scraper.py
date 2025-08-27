import requests
import json

# --- AYARLAR ---
# API URL'sini isteğiniz üzerine güncelledim.
API_URL = "https://c.appbaqend.com/show_valued"

# Çıktı olarak oluşturulacak dosyanın adı
OUTPUT_FILE = "playlist.m3u"

# M3U dosyasının başlık formatı
M3U_HEADER = "#EXTM3U\n"
# Her bir kanal için M3U formatı
M3U_TEMPLATE = '#EXTINF:-1 tvg-logo="" group-title="{group}",{name}\n{url}\n'

def fetch_and_create_playlist():
    """
    API'den yayın verilerini çeker ve gruplandırılmış bir M3U dosyası oluşturur.
    """
    print("API'den yayın listesi çekiliyor...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://yakatv4.live/'
        }
        
        response = requests.get(API_URL, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        if 'channels' not in data or not data['channels']:
            print("API yanıtında 'channels' listesi bulunamadı veya liste boş.")
            return

        events = data['channels']
        print(f"Toplam {len(events)} yayın bulundu. M3U dosyası oluşturuluyor...")
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(M3U_HEADER)
            
            for event in events:
                channel_name = event.get('name', 'Bilinmeyen Yayın')
                stream_url = event.get('url', '')
                group_name = event.get('category_name', 'Diğer')

                if stream_url:
                    f.write(M3U_TEMPLATE.format(
                        group=group_name,
                        name=channel_name,
                        url=stream_url
                    ))
                    
        print(f"'{OUTPUT_FILE}' dosyası başarıyla güncellendi.")

    except requests.exceptions.RequestException as e:
        print(f"API'ye bağlanırken bir hata oluştu: {e}")
    except Exception as e:
        print(f"Beklenmedik bir hata oluştu: {e}")


if __name__ == "__main__":
    fetch_and_create_playlist()