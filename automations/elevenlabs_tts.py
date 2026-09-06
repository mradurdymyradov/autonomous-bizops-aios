import os
import json
import requests

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

def find_voice(name="Denophine"):
    url = "https://api.elevenlabs.io/v1/voices"
    r = requests.get(url, headers={"xi-api-key": API_KEY})
    if r.status_code != 200:
        print("Error fetching voices:", r.status_code, r.text)
        return None
    voices = r.json().get("voices", [])
    for v in voices:
        if name.lower() in v["name"].lower():
            print(f"Found voice: {v['name']} (ID: {v['voice_id']})")
            return v["voice_id"]
    print(f"Voice '{name}' not found directly. Listing first 10 available voices:")
    for v in voices[:10]:
        print(f"- {v['name']} (ID: {v['voice_id']})")
    # If not found, check shared library or return first match
    return voices[0]["voice_id"] if voices else None

def generate_tts():
    voice_id = find_voice("Denophine")
    if not voice_id:
        print("No voice ID available.")
        return

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

    print(f"Generating ElevenLabs speech with voice {voice_id}...")
    r = requests.post(url, headers=HEADERS, json=payload)
    
    if r.status_code == 200:
        out_path = "d:/ai projects/vaios/assets/voiceover.mp3"
        os.makedirs("d:/ai projects/vaios/assets", exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(r.content)
        print(f"ElevenLabs voiceover successfully saved to: {out_path} ({len(r.content)} bytes)")
        
        # Also copy to reels project
        reels_audio = "d:/ai projects/vaios/reels-voronka-01/media/voiceover.mp3"
        if os.path.exists("d:/ai projects/vaios/reels-voronka-01/media"):
            with open(reels_audio, "wb") as f:
                f.write(r.content)
            print(f"Copied audio to {reels_audio}")
    else:
        print(f"TTS generation failed ({r.status_code}):", r.text)

if __name__ == "__main__":
    generate_tts()
