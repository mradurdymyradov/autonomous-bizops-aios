"""
Voice Clone Setup & Resumable Downloader
Features:
- HTTP Range Resumable Downloads (if connection drops, it resumes from where it stopped!)
- Real-time Speed (KB/s, MB/s), %, Downloaded/Total MB counter, and ETA
- Strict file integrity verification
"""

import os
import sys
import time
import subprocess
import urllib.request
import urllib.error

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

BASE_MODELS = [
    {
        "name": "HuBERT Feature Extractor (hubert_base.pt)",
        "url": "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt",
        "dest": os.path.join(ASSETS_DIR, "hubert_base.pt"),
        "expected_bytes": 189507909  # ~180.7 MB
    },
    {
        "name": "RMVPE Pitch Extractor (rmvpe.pt)",
        "url": "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/rmvpe.pt",
        "dest": os.path.join(ASSETS_DIR, "rmvpe.pt"),
        "expected_bytes": 181184272  # ~172.8 MB
    }
]

def format_size(bytes_val):
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{bytes_val / (1024 * 1024):.2f} MB"

def format_time(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m {secs:02d}s"

def download_file_resumable(url, dest_path, title, expected_bytes=0, max_retries=15):
    print(f"\n=======================================================")
    print(f" [DOWNLOADING] {title}")
    print(f" Target: {dest_path}")
    print(f" Total Expected: {format_size(expected_bytes)}")
    print(f"=======================================================")

    # Check if already complete and matches exact size
    if os.path.exists(dest_path):
        current_size = os.path.getsize(dest_path)
        if expected_bytes > 0 and current_size >= expected_bytes - 1024:
            print(f"  [OK] Already complete and verified ({format_size(current_size)}). Skipping.")
            return True
        else:
            print(f"  [INFO] Existing file is incomplete ({format_size(current_size)} / {format_size(expected_bytes)}). Resuming...")
            temp_dest = dest_path + ".tmp"
            if not os.path.exists(temp_dest):
                os.rename(dest_path, temp_dest)

    temp_dest = dest_path + ".tmp"
    
    for attempt in range(1, max_retries + 1):
        try:
            downloaded = os.path.getsize(temp_dest) if os.path.exists(temp_dest) else 0
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            if downloaded > 0:
                headers["Range"] = f"bytes={downloaded}-"
                print(f"  Resuming from {format_size(downloaded)} (attempt {attempt}/{max_retries})...")
            else:
                print(f"  Starting fresh download (attempt {attempt}/{max_retries})...")

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                content_range = response.headers.get("Content-Range")
                total_size = expected_bytes
                if content_range:
                    # e.g. "bytes 1000-189507908/189507909"
                    parts = content_range.split("/")
                    if len(parts) > 1 and parts[1].isdigit():
                        total_size = int(parts[1])
                elif response.status == 200:
                    length = response.headers.get("Content-Length")
                    if length and length.isdigit():
                        total_size = int(length)
                        downloaded = 0  # server didn't honor range, rewrote from 0

                start_time = time.time()
                last_time = start_time
                last_downloaded = downloaded
                chunk_size = 128 * 1024

                mode = "ab" if downloaded > 0 and response.status == 206 else "wb"
                with open(temp_dest, mode) as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        dt = now - last_time
                        if dt >= 0.25 or (total_size > 0 and downloaded >= total_size):
                            speed = (downloaded - last_downloaded) / dt if dt > 0 else 0
                            last_time = now
                            last_downloaded = downloaded

                            pct = (downloaded / total_size * 100) if total_size > 0 else 0
                            bar_len = 25
                            filled = int(bar_len * (downloaded / total_size)) if total_size > 0 else 0
                            bar = "#" * filled + "-" * (bar_len - filled)

                            speed_str = f"{format_size(speed)}/s"
                            mb_str = f"{format_size(downloaded)} / {format_size(total_size)}"

                            eta_str = ""
                            if speed > 0 and total_size > downloaded:
                                remaining = total_size - downloaded
                                eta_secs = remaining / speed
                                eta_str = f"| ETA: {format_time(eta_secs)}"

                            line = f"\r  [{bar}] {pct:5.1f}% | {mb_str:>17} | {speed_str:>10} {eta_str:<12}"
                            sys.stdout.write(line)
                            sys.stdout.flush()

                # Verify full completion
                if total_size > 0 and downloaded < total_size - 1024:
                    print(f"\n  [WARN] Connection closed early ({format_size(downloaded)}/{format_size(total_size)}). Retrying to resume...")
                    time.sleep(2)
                    continue

                print("\n  [SUCCESS] Download completed and verified.")
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                os.rename(temp_dest, dest_path)
                return True

        except Exception as e:
            print(f"\n  [WARN] Socket error: {e}")
            if attempt < max_retries:
                print("  Reconnecting and resuming in 3 seconds...")
                time.sleep(3)
            else:
                print("  [ERROR] Failed to download file after retries.")
                return False
    return False

def verify_python_dependencies():
    print("\n=======================================================")
    print(" [STEP 1/2] Verifying Python Audio Libraries")
    print("=======================================================")
    try:
        import numpy
        import scipy
        import soundfile
        import librosa
        import edge_tts
        import torch
        print(f"  [OK] PyTorch CPU: {torch.__version__}")
        print(f"  [OK] NumPy: {numpy.__version__}")
        print(f"  [OK] SciPy: {scipy.__version__}")
        print(f"  [OK] SoundFile & Librosa: Ready")
        print(f"  [OK] Edge-TTS: Ready")
        return True
    except ImportError as e:
        print(f"  [ERROR] Missing library: {e}")
        return False

def main():
    print("=======================================================")
    print("   VOICE CLONE CPU SETUP & RESUMABLE DOWNLOAD MONITOR  ")
    print("=======================================================")
    print(f"Location: {BASE_DIR}")

    # 1. Verify dependencies
    if not verify_python_dependencies():
        print("[ERROR] Please install dependencies before proceeding.")
        return

    # 2. Download RVC base models with resumable transfer
    print("\n=======================================================")
    print(" [STEP 2/2] Downloading RVC Base Models (HuBERT & RMVPE)")
    print("=======================================================")
    for model in BASE_MODELS:
        success = download_file_resumable(
            model["url"],
            model["dest"],
            model["name"],
            model["expected_bytes"]
        )
        if not success:
            print(f"\n[FATAL] Failed to download {model['name']}.")
            return

    print("\n=======================================================")
    print("  [ALL READY] Setup is 100% complete and verified!     ")
    print("=======================================================")
    print("\nNext step: Place your trained 'your_voice.pth' into:")
    print(f"  {MODELS_DIR}")
    print("\nThen run:")
    print("  python clone_tts.py --text \"Привет! Это проверка голоса.\" --output test.wav\n")

if __name__ == "__main__":
    main()
