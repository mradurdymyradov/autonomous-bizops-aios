import asyncio
import edge_tts
import json
import os

TEXT = (
    "Заявки из Инстаграма приносит не красивый профиль, а система. "
    "Таргетированная реклама приводит человека на сайт. "
    "За десять секунд он оставляет номер телефона, и заявка сразу падает вам в Telegram и CRM-таблицу. "
    "Ни один клиент не теряется. "
    "Хотите такую систему в своём бизнесе? Ссылка на бесплатный аудит — в шапке профиля."
)

VOICE = "ru-RU-DmitryNeural"
OUTPUT_AUDIO = "d:/ai projects/vaios/assets/voiceover.mp3"
OUTPUT_VTT = "d:/ai projects/vaios/assets/subtitles.vtt"

async def main():
    os.makedirs("d:/ai projects/vaios/assets", exist_ok=True)
    print(f"Generating audio with {VOICE}...")
    communicate = edge_tts.Communicate(TEXT, VOICE, rate="+5%", pitch="+0Hz")
    
    submaker = edge_tts.SubMaker()
    with open(OUTPUT_AUDIO, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])

    with open(OUTPUT_VTT, "w", encoding="utf-8") as file:
        file.write(submaker.generate_subs())

    print(f"Audio saved to: {OUTPUT_AUDIO}")
    print(f"Subtitles saved to: {OUTPUT_VTT}")

if __name__ == "__main__":
    asyncio.run(main())
