"""Local Russian transcription for HyperFrames using GigaAM v3 E2E CTC.

Outputs HyperFrames' normalized word-array JSON format:
[{"text": "...", "start": 0.0, "end": 0.4}, ...]
"""

from __future__ import annotations

import argparse
import audioop
import json
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path


DEFAULT_INSTALL = Path(r"D:\hyperframes\gigaam")
MODEL_NAME = "v3_e2e_ctc"
SAMPLE_RATE = 16_000
MAX_CHUNK_SECONDS = 24.0
SEARCH_FROM_SECONDS = 18.0
WINDOW_SECONDS = 0.02


def convert_to_wav(source: Path, target: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required but was not found on PATH")
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        check=True,
    )


def choose_chunk_frames(raw: bytes, sample_width: int) -> int:
    bytes_per_frame = sample_width
    total_frames = len(raw) // bytes_per_frame
    max_frames = int(MAX_CHUNK_SECONDS * SAMPLE_RATE)
    if total_frames <= max_frames:
        return total_frames

    search_start = int(SEARCH_FROM_SECONDS * SAMPLE_RATE)
    window_frames = int(WINDOW_SECONDS * SAMPLE_RATE)
    best_frame = max_frames
    best_rms: int | None = None
    for frame in range(search_start, max_frames, window_frames):
        start = frame * bytes_per_frame
        window = raw[start : start + window_frames * bytes_per_frame]
        rms = audioop.rms(window, sample_width)
        if best_rms is None or rms < best_rms:
            best_rms = rms
            best_frame = frame + window_frames // 2
    return best_frame


def split_wav(source: Path, directory: Path) -> list[tuple[Path, float]]:
    with wave.open(str(source), "rb") as reader:
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()
        sample_rate = reader.getframerate()
        raw = reader.readframes(reader.getnframes())

    if channels != 1 or sample_width != 2 or sample_rate != SAMPLE_RATE:
        raise RuntimeError("internal WAV conversion did not produce mono 16 kHz PCM16")

    chunks: list[tuple[Path, float]] = []
    offset_frames = 0
    remaining = raw
    while remaining:
        frames = choose_chunk_frames(remaining, sample_width)
        chunk_bytes = remaining[: frames * sample_width]
        chunk_path = directory / f"chunk-{len(chunks):04d}.wav"
        with wave.open(str(chunk_path), "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(sample_width)
            writer.setframerate(sample_rate)
            writer.writeframes(chunk_bytes)
        chunks.append((chunk_path, offset_frames / sample_rate))
        offset_frames += frames
        remaining = remaining[frames * sample_width :]
    return chunks


def transcribe(source: Path, output: Path, install_dir: Path) -> None:
    import gigaam

    model_dir = install_dir / "models"
    temp_dir = install_dir / "tmp"
    model_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {MODEL_NAME} on CPU...")
    model = gigaam.load_model(
        MODEL_NAME,
        device="cpu",
        fp16_encoder=False,
        use_flash=False,
        download_root=str(model_dir),
    )

    normalized: list[dict[str, float | str]] = []
    with tempfile.TemporaryDirectory(dir=temp_dir) as temp_name:
        working = Path(temp_name)
        wav_path = working / "audio.wav"
        print("Preparing 16 kHz mono audio...")
        convert_to_wav(source, wav_path)
        chunks = split_wav(wav_path, working)
        print(f"Transcribing {len(chunks)} chunk(s)...")
        for index, (chunk_path, offset) in enumerate(chunks, start=1):
            print(f"  [{index}/{len(chunks)}] {offset:.1f}s")
            result = model.transcribe(str(chunk_path), word_timestamps=True)
            for word in result.words or []:
                normalized.append(
                    {
                        "text": word.text,
                        "start": round(word.start + offset, 3),
                        "end": round(word.end + offset, 3),
                    }
                )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(normalized)} timed words to {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe Russian audio/video to HyperFrames word JSON"
    )
    parser.add_argument("input", type=Path, help="audio or video file")
    parser.add_argument("output", type=Path, help="output transcript JSON")
    parser.add_argument(
        "--install-dir", type=Path, default=DEFAULT_INSTALL, help="GigaAM install"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    transcribe(args.input.resolve(), args.output.resolve(), args.install_dir.resolve())
