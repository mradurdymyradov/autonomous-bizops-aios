import requests
import os

API_KEY = "sk_028a8b8cf360189c097f3c4e23768085a9ab837e38ef3c4d"
HEADERS = {
    "xi-api-key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "audio/mpeg"
}

SCRIPT_TEXT = (
    "Заявки из Инстаграма приносит не красивый профиль, а система. "
    "Таргетированная реклама приводит человека на сайт. "
    "За десять секунд он оставляет номер телефона, и заявка сразу падает вам в Telegram и CRM-таблицу. "
    "Ни один клиент не теряется. "
    "Хотите такую систему в своём бизнесе? Ссылка на бесплатный аудит — в шапке профиля."
)

# Test with Liam (Energetic, Social Media Creator) or Charlie
voice_id = "TX3LPaxmHKxFdv7VOQHJ" # Liam

url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
payload = {
    "text": SCRIPT_TEXT,
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {
        "stability": 0.61,
        "similarity_boost": 0.72,
        "style": 0.63,
        "use_speaker_boost": False
    }
}

print("Testing generation with premade voice Liam...")
r = requests.post(url, headers=HEADERS, json=payload)
print("Status:", r.status_code)
if r.status_code == 200:
    out = "d:/ai projects/vaios/assets/voiceover_elevenlabs.mp3"
    with open(out, "wb") as f:
        f.write(r.content)
    print(f"Saved to {out} ({len(r.content)} bytes)")
else:
    print("Response:", r.text)
