import requests
import json
import os

API_KEY = "sk_V2_hgu_kncn3ccBGZR_EO5tuvsZFRpSWzBCYbutkdLnBpcQHimb"
HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}

text = "Заявки из Инстаграма приносит не красивый профиль, а система. Таргетированная реклама приводит человека на сайт, за десять секунд он оставляет номер, и заявка сразу падает вам в Telegram и CRM-таблицу. Ссылка на бесплатный аудит — в шапке профиля."
voice_id = "6iyXVhsIZxvUx1RjtM1m" # The cloned voice!

endpoints = [
    ("v2_audio_tts", "https://api.heygen.com/v2/audio/tts", {"text": text, "voice_id": voice_id}),
    ("v1_voice_tts", "https://api.heygen.com/v1/voice/tts", {"text": text, "voice_id": voice_id}),
    ("v2_tts", "https://api.heygen.com/v2/tts", {"text": text, "voice_id": voice_id}),
    ("v1_audio_create", "https://api.heygen.com/v1/audio/create", {"text": text, "voice_id": voice_id})
]

for name, url, payload in endpoints:
    print(f"\nTesting endpoint: {name} ({url})...")
    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        print(f"Status: {r.status_code}")
        print("Response:", r.text[:300])
    except Exception as e:
        print("Error:", e)
