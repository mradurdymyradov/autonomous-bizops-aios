"""
Edge-TTS + RVC v2 Voice Synthesis Pipeline
Ultra-lightweight local voice synthesis for 1 cloned voice.

Usage:
  python clone_tts.py --text "Привет! Это озвучка моим клонированным голосом."
  python clone_tts.py --file script.txt --output voiceover.wav
"""

import os
import sys
import asyncio
import argparse
import edge_tts

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

async def generate_base_tts(text: str, voice: str, output_path: str):
    """Generate high-quality base audio via edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def synthesize_cloned(
    text: str,
    output_path: str = "output.wav",
    model_name: str = None,
    base_voice: str = "ru-RU-DmitryNeural",
    pitch_shift: int = 0
):
    # Find model in models/
    if model_name:
        model_path = os.path.join(MODELS_DIR, model_name)
    else:
        # Auto-detect first .pth model in models directory
        pth_files = [f for f in os.listdir(MODELS_DIR) if f.endswith(".pth")] if os.path.exists(MODELS_DIR) else []
        if not pth_files:
            print(f"[ERROR] No trained .pth voice model found in '{MODELS_DIR}'.")
            print("Please place your trained 'your_voice.pth' into the models/ folder.")
            return False
        model_path = os.path.join(MODELS_DIR, pth_files[0])
        print(f"[INFO] Using detected voice model: {pth_files[0]}")

    # Look for matching .index file
    index_files = [f for f in os.listdir(MODELS_DIR) if f.endswith(".index")] if os.path.exists(MODELS_DIR) else []
    index_path = os.path.join(MODELS_DIR, index_files[0]) if index_files else None

    temp_base_wav = os.path.join(BASE_DIR, "_temp_base.wav")

    print(f"\n[1/2] Generating baseline neural speech with {base_voice}...")
    asyncio.run(generate_base_tts(text, base_voice, temp_base_wav))

    print(f"[2/2] Converting voice timbre via RVC (CPU)...")
    try:
        from rvc_python.infer import RVCInference
        rvc = RVCInference(device="cpu")
        rvc.load_model(model_path, index_path=index_path)
        rvc.infer_file(
            input_path=temp_base_wav,
            output_path=output_path,
            f0_method="pm",
            f0_up_key=pitch_shift
        )
        print(f"\n[SUCCESS] Audio successfully generated: {output_path}")
        return True
    except Exception as e:
        print(f"[ERROR] RVC conversion failed: {e}")
        return False
    finally:
        if os.path.exists(temp_base_wav):
            try:
                os.remove(temp_base_wav)
            except Exception:
                pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edge-TTS + RVC Voice Cloning Synthesizer")
    parser.add_argument("--text", "-t", type=str, help="Text to speak")
    parser.add_argument("--file", "-f", type=str, help="Path to text file to speak")
    parser.add_argument("--output", "-o", type=str, default="output.wav", help="Output .wav path")
    parser.add_argument("--model", "-m", type=str, default=None, help="Voice model .pth file name inside models/")
    parser.add_argument("--voice", "-v", type=str, default="ru-RU-DmitryNeural", help="Base voice (e.g. ru-RU-DmitryNeural, ru-RU-SvetlanaNeural, en-US-GuyNeural)")
    parser.add_argument("--pitch", "-p", type=int, default=0, help="Pitch shift semitones (0 = unchanged, +12 = octave up)")
    
    args = parser.parse_args()
    
    input_text = args.text
    if args.file and os.path.exists(args.file):
        with open(args.file, "r", encoding="utf-8") as f:
            input_text = f.read().strip()
            
    if not input_text:
        print("Please provide text using --text \"...\" or --file script.txt")
        sys.exit(1)
        
    synthesize_cloned(
        text=input_text,
        output_path=args.output,
        model_name=args.model,
        base_voice=args.voice,
        pitch_shift=args.pitch
    )
