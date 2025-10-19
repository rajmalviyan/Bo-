import re
import certifi
import os
import requests

# Add the channel logo constant
CHANNEL_LOGO = "https://github.com/BuddyChewChew/gen-playlist/blob/main/docs/ch.png?raw=true"

def runServers():

    # Create a single combined playlist file with EPG URL
    with open("docs/combined_playlist.m3u", "w", encoding='utf-8-sig') as file:
        file.write("#EXTM3U x-tvg-url=\"https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz\"\n")

    # Process each server and append to the combined playlist

    for i in range(len(hashCode)):
        print(f"{i+1}.{channels[i]}")
        server1(hashCode[i], channels[i])

    for i in range(len(hashcode_2)):
        print(f"{i+1}.{channels_2[i]}")
        server2(hashcode_2[i], channels_2[i])
        
    try:    
        with open("docs/combined_playlist.m3u", "a", encoding='utf-8-sig') as file:
            file.write(f'#EXTINF:-1 tvg-id="Adult.Programming.Dummy.us" tvg-name="" tvg-logo="{CHANNEL_LOGO}" group-title="Adult 2",okLiveTV\n')
            file.write(f"https://oklivetv.com/xplay/m3u8/N1VQM0VBOUNWbVZwQzZOZUpSR3JVZz09.m3u8\n") 
    except Exception as e:
        print(f"Error processing {name}: {str(e)}")    

def server1(hash, name):
    print("Running Server 1")
    try:
        res = requests.post(
            f"https://adult-tv-channels.click/C1Ep6maUdBIeKDQypo7a/{hash}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        data = res.json()
        token = data["fileUrl"]
        stream_url = f"https://moonlight.wideiptv.top/{name}/index.fmp4.m3u8?token={token}"
        with open("docs/combined_playlist.m3u", "a", encoding='utf-8-sig') as file:
            file.write(f'#EXTINF:-1 tvg-id="Adult.Programming.Dummy.us" tvg-name="{name}" tvg-logo="{CHANNEL_LOGO}" group-title="Adult 1",{name}\n')
            file.write(f"{stream_url}\n")
    except Exception as e:
        print(f"Error processing {name}: {str(e)}")

def server2(hash, name):
    print("Running Server 2")
    try:
        url = f"https://fuckflix.click/8RLxsc2AW1q8pvyvjqIQ"
        res = requests.post(
            f"{url}/{hash}", 
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        data = res.json()
        token = data["fileUrl"]
        stream_url = f"https://moonlight.wideiptv.top/{name}/index.fmp4.m3u8?token={token}"
        with open("docs/combined_playlist.m3u", "a", encoding='utf-8-sig') as file:
            file.write(f'#EXTINF:-1 tvg-id="Adult.Programming.Dummy.us" tvg-name="{name}" tvg-logo="{CHANNEL_LOGO}" group-title="Adult 2",{name}\n')
            file.write(f"{stream_url}\n")
    except Exception as e:
        print(f"Error processing {name}: {str(e)}")

# for Server 1
hashCode = [
    "Sdw0p0xE3E",
    "yoni9C8jfd",
    "ZS40W182Zq",
    "czS16artgz",
    "xBFRYv6yXh",
    "hghdvp9Z03",
    "ByYpxFkJZe",
    "5LvPjA7oms",
    "HdcCGPssEy",
    "sI8DBZkklJ",
    "sSEWMS7slF",
    "dRTbLz32p7",
    "Sd6GJ5uMmj",
    "IDLur5k1x2",
    "4FVedsyYlB",
    "S8XdeQ0R1t",
    "svpUwVLRR8",
    "A2PZR5jdH8",
    "3uGUuSP7HX",
    "oEd93JisZ3",
    "E3WyHBCn6j",
    "5QeEhtMv0v",
    "ZQgSJJmzAx",
    "JTzDFcBdgp",
    "58Nyzda2hb",
    "ZvBCE7cpgP",
    "V2D4lPbasF",
    "t6VXUhiBYF",
    "JiA1DWNWJc",
    "RMdBtgPkAZ",
    "D9QT1n9SFy",
    "HdcCGPssEy",
    "qzVwPIpnOJ",
]

channels = [
    "ExxxoticaTV",
    "LeoTV",
    "LeoGoldTV",
    "EvilAngel",
    "VIXEN",
    "Extasy4K",
    "PinkoClubTV",
    "BrazzersTVEU",
    "HustlerHD",
    "RedlightHD",
    "SecretCircleTV",
    "PenthouseGold",
    "Television-X",
    "Private",
    "HOT-HD",
    "BODYSEX",
    "DorcelTV",
    "TransAngels",
    "SuperONE",
    "SextremeTV",
    "SeXation",
    "PassionXXX",
    "HustlerTV",
    "EroX-XxX",
    "EroLuxeShemales",
    "DesireTV",
    "CentoXCento",
    "Barely-Legal-TV",
    "Venus",
    "True-Amateurs",
    "SexPrive",
    "HustlerHD",
    "HotPleasure",
]

# for Server 1

hashcode_2 = [
    "5LvPjA7oms",
    "CudzGm9xm6",
    "T3PIyktDDU",
    "9itOC3AHqJ",
    "OWMDBFfu89",
    "QOOfbBqT4v",
    "2x7HptDKuX",
    "esdMCy0VGM",
    "6s6dIMWGXi",
    "Sdw0p0xE3E",
    "ZS40W182Zq",
    "yoni9C8jfd",
    "czS16artgz",
    "hghdvp9Z03",
    "xBFRYv6yXh",
    "E3WyHBCn6j",
    "HdcCGPssEy",
    "ByYpxFkJZe",
    "Sd6GJ5uMmj",
    "t6VXUhiBYF",
    "58Nyzda2hb",
    "sSEWMS7slF",
    "s4URaZHdvZ",
    "sI8DBZkklJ",
    "YC81XHWeHu",
    "v3UeIcgWXa",
    "dRTbLz32p7",
    "IDLur5k1x2",
    "JAZlXsiLni",
    "R4ol8r2lki",
    "kpTVK5NF1w",
    "m6Elk7hY4x",
    "S8XdeQ0R1t",
    "4FVedsyYlB",
    "svpUwVLRR8",
    "A2PZR5jdH8",
    "3uGUuSP7HX",
    "oEd93JisZ3",
    "5QeEhtMv0v",
    "ZQgSJJmzAx",
    "JTzDFcBdgp",
    "ZvBCE7cpgP",
    "V2D4lPbasF",
    "JiA1DWNWJc",
    "jK2r6H1Dlj",
    "RMdBtgPkAZ",
    "D9QT1n9SFy",
    "HdcCGPssEy",
    "qzVwPIpnOJ",
    "B23u2g9du7",
    "JGjj7Rdr6i",
    "jrg0w1yR2h",
    "gnZXsccuUp",
    "e73aEtFcbZ",
    "1oBa1u9iyV",
    "ATi9uJZMuW",
    "WT9UjJnroi",
    "4evZjk9isU",
    "hghdvp9Z03",
    "ARoRH5Bnk4",
    "NTWRHBE1Pj",
    "H2qfNxdFda",
    "JvifgL9Khz",
    "CeGVJHRYL1",
    "uFZFNiL2hb",
]

channels_2 = [
    "BrazzersTVEU",
    "Tiny4k1",
    "Tiny4k2",
    "Tiny4k3",
    "PenthouseBLACK",
    "Penthouse",
    "NuartTV",
    "Mofos",
    "cum4k",
    "ExxxoticaTV",
    "LeoGoldTV",
    "LeoTV",
    "EvilAngel",
    "Extasy4K",
    "VIXEN",
    "SeXation",
    "HustlerHD",
    "PinkoClubTV",
    "Television-X",
    "Barely-Legal-TV",
    "EroLuxeShemales",
    "SecretCircleTV",
    "Beate-Uhse",
    "RedlightHD",
    "DorcelTVAfrica",
    "PlayboyTV",
    "PenthouseGold",
    "Private",
    "HOTMan",
    "SexyHOT",
    "TransErotica",
    "HOTXXL",
    "BODYSEX",
    "HOT-HD",
    "DorcelTV",
    "TransAngels",
    "SuperONE",
    "SextremeTV",
    "PassionXXX",
    "HustlerTV",
    "EroX-XxX",
    "DesireTV",
    "CentoXCento",
    "Venus",
    "XXL",
    "True-Amateurs",
    "SexPrive",
    "HustlerHD",
    "HotPleasure",
    "VividTV",
    "FAKETAXI",
    "Dusk",
    "BlueHustler",
    "BangU",
    "Babes",
    "RealityKingsTV",
    "PenthouseNN",
    "PenthouseAFM",
    "Extasy4K",
    "PenthouseRealityTV",
    "PenthousePassion",
    "4kporn",
    "4kporn2",
    "4kporn3",
    "4kporn4",
]

runServers()  # Runs the function to start the servers!
