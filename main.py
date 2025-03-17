import requests
import json
import re
import time
from flask import Flask
import threading

app = Flask(__name__)

# Konfigürasyon
API_URL = "https://web.dunyagoz.com/dghnet/dghsite.asmx/GetDoctorSlots"
API_KEY = "TMABkbhx2cyFWYyF2SuFGb5FGVAl2cl5WY0NXYIp3bnFWeuVHRhsEdAVDN4cjN1I"
RESOURCE_ID = "5637176076"
FACILITY_ID = "5637145326"
WEBHOOK_URL = "https://discordapp.com/api/webhooks/1218828382918152235/6n55PViv34tX-w76mv1NF9JqGSwL63GpKt4wdCwaDK90kpRUe9vA-IaXJuPSHKd7JEEb"
CHECK_DATES = ["22.03.2025", "23.03.2025"]

# Daha önce bildirilen slotları saklamak için
notified_slots = set()

def fetch_slots():
    """API'den doktor slotlarını çeker ve XML içindeki JSON'u ayrıştırır."""
    new_slots = []
    for date in CHECK_DATES:
        params = {
            "ApiKey": API_KEY,
            "SlotDate": date,
            "ResourceId": RESOURCE_ID,
            "FacilityId": FACILITY_ID,
        }
        
        try:
            response = requests.get(API_URL, params=params)
            response.raise_for_status()
            
            if not response.text or response.text.strip() == "":
                print(f"⚠️ API'den boş yanıt alındı: {date}")
                continue
            
            # XML içindeki JSON verisini temizleyelim
            json_text = re.search(r"<string xmlns=.*?>(.*?)</string>", response.text, re.DOTALL)
            if not json_text:
                print(f"⚠️ XML içinde JSON verisi bulunamadı. API Yanıtı: {response.text}")
                continue
            
            json_data = json_text.group(1).strip()
            
            if not (json_data.startswith("{") and json_data.endswith("}")):
                print(f"⚠️ Geçersiz JSON yanıtı: {json_data}")
                continue
            
            try:
                data = json.loads(json_data)
                slots = data.get("RESPONSE", {}).get("LIST", [])
                
                for slot in slots:
                    if slot.get("SLOT_DATE") == date:
                        for time_slot in slot.get("SLOT_TIME_LIST", []):
                            if time_slot.get("TIME") and "IS_AVAILABLE" in time_slot:
                                slot_key = f"{slot['SLOT_DATE']} - {time_slot['TIME']}"
                                if time_slot["IS_AVAILABLE"] and slot_key not in notified_slots:
                                    new_slots.append(slot_key)
                                    notified_slots.add(slot_key)
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON Parse Hatası: {e} | Yanıt: {json_data}")
                continue
        
        except requests.RequestException as e:
            print(f"⚠️ API isteği başarısız: {e}")
            continue
    
    return new_slots

def check_available_slots():
    """Yeni boş slot olup olmadığını kontrol eder ve Discord'a bildirir."""
    new_slots = fetch_slots()
    
    if new_slots:
        message = "\n".join(new_slots)
        send_discord_message(message)
    else:
        print("ℹ️ Yeni boş slot bulunamadı, tekrar kontrol edilecek.")

def send_discord_message(message):
    """Discord Webhook'a mesaj gönderir."""
    data = {"content": f"✅ Yeni Boş Randevu Slotları Bulundu!\n{message}"}
    response = requests.post(WEBHOOK_URL, json=data)
    if response.status_code == 204:
        print("✅ Mesaj başarıyla gönderildi.")
    else:
        print(f"⚠️ Discord mesaj gönderme hatası: {response.status_code} - {response.text}")

def run_scheduler():
    """15 dakikada bir slotları kontrol eder."""
    while True:
        check_available_slots()
        time.sleep(900)  # 15 dakika bekle

@app.route('/')
def home():
    return "Randevu Kontrol Botu Çalışıyor!"

@app.route('/status')
def status():
    return {
        "status": "running",
        "message": "Randevu Kontrol Botu aktif ve çalışıyor!",
    }, 200

if __name__ == '__main__':
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)