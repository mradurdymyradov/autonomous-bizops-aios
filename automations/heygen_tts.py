import os
import sys
import json
import requests

HEYGEN_API_KEY = os.environ.get("HEYGEN_API_KEY", "")

def generate_voiceover(text, voice_id="2d5b0e6cf36f460aa7fc47e3eee4ba54", output_path="assets/voiceover.mp3"):
    """
    Generates TTS audio via HeyGen API.
    voice_id: Russian voices include e.g. Dmitry, Oleg, Anya or custom cloned voice.
    """
    if not HEYGEN_API_KEY:
        print("Error: HEYGEN_API_KEY environment variable is not set.")
        print("Please set your HeyGen API key: export HEYGEN_API_KEY='your_key' or pass it.")
        sys.exit(1)

    url = "https://api.heygen.com/v2/audio/tts" # or v1 voice endpoints
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_id": voice_id
    }

    print(f"Requesting HeyGen TTS for text: {text[:60]}...")
    res = requests.post(url, headers=headers, json=payload)
    print("Status code:", res.status_code)
    try:
        data = res.json()
        print("Response:", json.dumps(data, indent=2))
        if res.status_code == 200 and "data" in data and "audio_url" in data["data"]:
            audio_url = data["data"]["audio_url"]
            audio_res = requests.get(audio_url)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_res.content)
            print(f"Successfully saved voiceover to {output_path}")
            return output_path
    except Exception as e:
        print("Error parsing response:", e)
        print("Raw text:", res.text)

if __name__ == "__main__":
    test_text = "Заявки из Инстаграма приносит не красивый профиль, а система."
    generate_voiceover(test_text)
