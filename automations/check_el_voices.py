import requests

API_KEY = "sk_028a8b8cf360189c097f3c4e23768085a9ab837e38ef3c4d"
url = "https://api.elevenlabs.io/v1/voices"
r = requests.get(url, headers={"xi-api-key": API_KEY})
voices = r.json().get("voices", [])

print("Available voices for this key:")
for v in voices:
    category = v.get("category", "")
    print(f"- {v['name']} | ID: {v['voice_id']} | Category: {category}")
