import os
import json
import requests

API_KEY = os.environ.get("HEYGEN_API_KEY", "")  # never hardcode: see automations/.env.heygen
HEADERS = {
    "X-Api-Key": API_KEY,
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def check_user():
    print("Checking HeyGen User & Quota...")
    r = requests.get("https://api.heygen.com/v1/user/remaining_quota", headers=HEADERS)
    print("User Quota Status:", r.status_code, r.text)

def list_voices():
    print("\nFetching Russian voices from HeyGen...")
    r = requests.get("https://api.heygen.com/v2/voices", headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        voices = data.get("data", {}).get("voices", [])
        ru_voices = [v for v in voices if v.get("language") in ["Russian", "ru", "ru-RU"] or "ru" in str(v.get("support_languages", [])).lower()]
        print(f"Found {len(ru_voices)} Russian voices.")
        for v in ru_voices[:10]:
            print(f"- Voice: {v.get('name')} | ID: {v.get('voice_id')} | Gender: {v.get('gender')}")
        return ru_voices
    else:
        print("Voices Error:", r.status_code, r.text)
        return []

if __name__ == "__main__":
    check_user()
    list_voices()
