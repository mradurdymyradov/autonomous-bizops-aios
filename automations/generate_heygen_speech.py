import os
import json
import requests

API_KEY = "sk_V2_hgu_kncn3ccBGZR_EO5tuvsZFRpSWzBCYbutkdLnBpcQHimb"
HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# The script for our Reel 1
SCRIPT_TEXT = "Заявки из Инстаграма приносит не красивый профиль, а система. Таргетированная реклама приводит человека на сайт, за десять секунд он оставляет номер, и заявка сразу падает вам в Telegram и CRM-таблицу. Ни один клиент не теряется. Хотите такую систему в своём бизнесе? Ссылка на бесплатный аудит — в шапке профиля."

# Voice ID (The cloned voice or Dmitry/Oleg)
VOICE_ID = "6iyXVhsIZxvUx1RjtM1m" # aimra - Voice 1

def generate():
    url = "https://api.heygen.com/v3/voices/speech"
    payload = {
        "text": SCRIPT_TEXT,
        "voice_id": VOICE_ID
    }

    print(f"Sending request to {url} with voice {VOICE_ID}...")
    r = requests.post(url, headers=HEADERS, json=payload)
    print("Status:", r.status_code)
    try:
        data = r.json()
        print("Response:", json.dumps(data, indent=2))
        
        # Check if audio_url or task_id is returned
        audio_url = data.get("data", {}).get("audio_url") or data.get("data", {}).get("url")
        if audio_url:
            print(f"Downloading audio from {audio_url}...")
            os.makedirs("d:/ai projects/vaios/assets", exist_ok=True)
            audio_data = requests.get(audio_url).content
            out_file = "d:/ai projects/vaios/assets/voiceover_heygen.mp3"
            with open(out_file, "wb") as f:
                f.write(audio_data)
            print(f"Voiceover successfully saved to: {out_file} ({len(audio_data)} bytes)")
            return out_file
        else:
            print("No direct audio_url, checking task response...")
    except Exception as e:
        print("Error:", e)
        print("Raw text:", r.text)

if __name__ == "__main__":
    generate()
