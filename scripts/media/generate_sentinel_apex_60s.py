#!/usr/bin/env python3
"""Render the 60-second Sentinel Apex / CYBERDUDEBIVASH Vijayadashami corporate video (4 acts x 15 s, 1920x1080, 30 fps).

Layout: a flat timeline of one background layer and one centre-locked text layer per act. Text sits in an 80 % title-safe box
and is rasterised with Pillow, so the render needs neither ImageMagick nor a font *name* resolved by the operating system.

Optional inputs (the video renders silent / on solid colours without them):
  --backdrop-dir DIR   act1.mp4 ... act4.mp4 (any of .mp4 .mov .webm .mkv) generated from the prompts in README.md
  --music FILE         looped or trimmed to 60 s, fades out over the last 1.5 s
  --voiceover FILE     placed at 0 s; the music is ducked by 12.5 dB under the cues in VOICEOVER_CUES

Run:  .venv/bin/pip install -r scripts/media/requirements.txt
      .venv/bin/python scripts/media/generate_sentinel_apex_60s.py            # writes dist/media/sentinel_apex_global_broadcast_60s.mp4
      .venv/bin/python scripts/media/generate_sentinel_apex_60s.py --preview 5   # 5-second smoke render
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "dist" / "media" / "sentinel_apex_global_broadcast_60s.mp4"   # dist/ is git-ignored: renders are build artefacts
ENGINE_BANNER = "Sentinel Apex Core Production Engine V40.0"

WIDTH, HEIGHT, FPS = 1920, 1080, 30
ACT_SECONDS = 15.0
FADE_SECONDS = 0.6
SAFE_RATIO = 0.8                       # text box = 80 % of the frame in both directions, centred
STROKE_WIDTH = 2
LINE_SPACING = 1.15

# Master voice-over cues (seconds). The music bed is ducked under each one.
VOICEOVER_CUES = ((2.0, 12.0), (17.0, 27.0), (32.0, 42.0))
MUSIC_BED_GAIN = 0.5                   # -6 dB; ducked bed = 0.5 x 10^(-12.5/20) ~= 0.12
DUCK_DB = -12.5
DUCK_ATTACK_SECONDS = 0.25             # ramp down this long *before* a cue starts
DUCK_RELEASE_SECONDS = 0.6             # ramp back up this long after a cue ends
MUSIC_FADEOUT_SECONDS = 1.5
AUDIO_FPS = 44100

BACKDROP_SUFFIXES = (".mp4", ".mov", ".webm", ".mkv")
FONT_ENV = "SENTINEL_APEX_FONT"
FONT_CANDIDATES = (                    # Arial Bold first; Liberation Sans Bold is its metric-compatible substitute
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


@dataclass(frozen=True)
class Act:
    name: str
    background: tuple[int, int, int]
    color: str                          # text colour (hex)
    font_size: int
    text: str


ACTS = (
    Act("black-box cyber manifesto", (8, 8, 12), "#FFFFFF", 62,
        "IN A HYPER-SCALE DIGITAL COMPLEXITY\nABSOLUTE RESILIENCE IS A MANDATE.\n\nSENTINEL APEX BRAND"),
    Act("flagship AI security hub", (12, 22, 32), "#00E5FF", 68,
        "SENTINEL APEX™\nENTERPRISE AI SECURITY PLATFORM\n\nwww.cyberdudebivash.in"),
    Act("command-centre threat telemetry", (10, 14, 20), "#FFFFFF", 58,
        "REAL-TIME ADVANCED THREAT INTEL\n& COMPLIANCE MAPPING\n\nintel.cyberdudebivash.com"),
    Act("sovereign festive triumph", (35, 25, 8), "#FFD700", 54,
        "CYBERDUDEBIVASH ECOSYSTEM®\n\nWISHING THE PRODUCTION CUSTOMERS\nA PROSPEROUS DUSSEHRA\n\nwww.cyberdudebivash.com"),
)
TOTAL_SECONDS = ACT_SECONDS * len(ACTS)


class MediaInputError(Exception):
    """A user-supplied input (font, footage, audio, option) is unusable. Maps to exit code 2."""


# ------------------------------------------------------------------------------------ pure helpers (no moviepy needed)

def resolve_font(explicit: Path | None = None) -> Path:
    requested = explicit or (Path(os.environ[FONT_ENV]) if os.environ.get(FONT_ENV) else None)
    if requested is not None:
        if not requested.is_file():
            raise MediaInputError(f"font not found: {requested}")
        return requested
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return Path(candidate)
    raise MediaInputError(f"no bold sans-serif font found; install Liberation Sans or pass --font / set {FONT_ENV}")


def wrap_text(text: str, font, max_width: float) -> list[str]:
    """Greedy word wrap of each paragraph line; blank lines are kept as vertical spacing. `font` needs only .getlength(str)."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for word in paragraph.split():
            trial = f"{current} {word}".strip()
            if current and font.getlength(trial) > max_width:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    return lines


def duck_gain(t, cues=VOICEOVER_CUES, duck_db: float = DUCK_DB, attack: float = DUCK_ATTACK_SECONDS, release: float = DUCK_RELEASE_SECONDS):
    """Gain multiplier for the music bed at time(s) `t`: 1.0 outside the cues, 10^(duck_db/20) inside, linear ramps between."""
    import numpy as np

    t = np.asarray(t, dtype=float)
    depth = np.zeros_like(t)
    for start, end in cues:
        ramp = np.minimum((t - (start - attack)) / attack, ((end + release) - t) / release)
        depth = np.maximum(depth, np.clip(ramp, 0.0, 1.0))
    return 1.0 - (1.0 - 10.0 ** (duck_db / 20.0)) * depth


def render_text_card(text: str, font_path: Path, font_size: int, color: str, box_width: int):
    """Rasterise centred, stroked text into an RGBA array exactly `box_width` wide. Raises if a single word cannot fit."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype(str(font_path), font_size)
    inner_width = box_width - 2 * STROKE_WIDTH
    lines = wrap_text(text, font, inner_width)
    too_wide = [ln for ln in lines if font.getlength(ln) > inner_width]
    if too_wide:
        raise MediaInputError(f"text does not fit the title-safe width at {font_size}px: {too_wide[0]!r}")
    ascent, descent = font.getmetrics()
    line_height = round((ascent + descent) * LINE_SPACING)
    card = Image.new("RGBA", (box_width, line_height * len(lines) + 2 * STROKE_WIDTH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    for row, line in enumerate(lines):
        if line:
            x = (box_width - font.getlength(line)) / 2
            draw.text((x, STROKE_WIDTH + row * line_height), line, font=font, fill=color, stroke_width=STROKE_WIDTH, stroke_fill="#000000")
    return np.asarray(card)


# ------------------------------------------------------------------------------------ moviepy assembly

def _moviepy():
    try:
        import moviepy.editor as mp
    except ImportError as exc:                       # moviepy 2.x removed `moviepy.editor`; the pinned 1.0.3 is required
        raise MediaInputError(f"moviepy 1.x is required ({exc}); run: pip install -r scripts/media/requirements.txt") from exc
    return mp


def find_backdrop(backdrop_dir: Path | None, act_number: int) -> Path | None:
    if backdrop_dir is None:
        return None
    for suffix in BACKDROP_SUFFIXES:
        candidate = backdrop_dir / f"act{act_number}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def background_layer(mp, act: Act, start: float, footage: Path | None):
    if footage is None:
        return mp.ColorClip(size=(WIDTH, HEIGHT), color=act.background).set_start(start).set_duration(ACT_SECONDS)
    import numpy as np
    from PIL import Image

    def cover(frame):                                # scale-to-cover + centre crop; Pillow directly, as moviepy 1.0.3 `resize` needs Pillow < 10
        h, w = frame.shape[:2]
        scale = max(WIDTH / w, HEIGHT / h)
        image = Image.fromarray(frame).resize((max(WIDTH, round(w * scale)), max(HEIGHT, round(h * scale))), Image.LANCZOS)
        left, top = (image.width - WIDTH) // 2, (image.height - HEIGHT) // 2
        return np.asarray(image.crop((left, top, left + WIDTH, top + HEIGHT)))

    clip = mp.VideoFileClip(str(footage), audio=False).fx(mp.vfx.loop, duration=ACT_SECONDS)
    return clip.fl_image(cover).set_start(start).set_duration(ACT_SECONDS)


def text_layer(mp, act: Act, start: float, font_path: Path):
    box_width = int(WIDTH * SAFE_RATIO)
    card = render_text_card(act.text, font_path, act.font_size, act.color, box_width)
    if card.shape[0] > HEIGHT * SAFE_RATIO:
        raise MediaInputError(f"act '{act.name}': text block is {card.shape[0]}px tall, over the {int(HEIGHT * SAFE_RATIO)}px title-safe height")
    return (mp.ImageClip(card)
            .set_position(("center", "center"))
            .set_start(start)
            .set_duration(ACT_SECONDS)
            .crossfadein(FADE_SECONDS)
            .crossfadeout(FADE_SECONDS))


def build_audio(mp, music: Path | None, voiceover: Path | None):
    if music is None and voiceover is None:
        return None
    tracks = []
    if music is not None:
        bed = mp.AudioFileClip(str(music))
        bed = bed.fx(mp.afx.audio_loop, duration=TOTAL_SECONDS) if bed.duration < TOTAL_SECONDS else bed.subclip(0, TOTAL_SECONDS)

        def gain(get_frame, t):
            g = MUSIC_BED_GAIN * (duck_gain(t) if voiceover is not None else 1.0)
            frames = get_frame(t)
            return frames * (g[:, None] if getattr(g, "ndim", 0) else g)

        tracks.append(bed.fl(gain, keep_duration=True).audio_fadeout(MUSIC_FADEOUT_SECONDS))
    if voiceover is not None:
        voice = mp.AudioFileClip(str(voiceover))
        tracks.append(voice.subclip(0, TOTAL_SECONDS) if voice.duration > TOTAL_SECONDS else voice)
    mix = mp.CompositeAudioClip(tracks)
    mix.fps = AUDIO_FPS
    return mix.set_duration(TOTAL_SECONDS)


def build_video(font_path: Path, backdrop_dir: Path | None = None, music: Path | None = None, voiceover: Path | None = None):
    mp = _moviepy()
    backgrounds, texts = [], []
    for index, act in enumerate(ACTS):
        start = index * ACT_SECONDS                  # flat timeline: every layer carries its own absolute start, nothing is offset twice
        backgrounds.append(background_layer(mp, act, start, find_backdrop(backdrop_dir, index + 1)))
        texts.append(text_layer(mp, act, start, font_path))
    video = mp.CompositeVideoClip(backgrounds + texts, size=(WIDTH, HEIGHT)).set_duration(TOTAL_SECONDS)
    audio = build_audio(mp, music, voiceover)
    return video.set_audio(audio) if audio is not None else video


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def render(video, output: Path, preview_seconds: float | None = None) -> None:
    """Encode to a temporary file and move it into place only on success, so a failed render never leaves a truncated asset."""
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(f"{output.stem}.partial{output.suffix}")
    clip = video.subclip(0, preview_seconds) if preview_seconds else video
    try:
        clip.write_videofile(str(partial), fps=FPS, codec="libx264", audio_codec="aac", audio_fps=AUDIO_FPS, preset="medium", logger=None,
                             ffmpeg_params=["-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart"])   # yuv420p + faststart: plays in browsers, phones, LinkedIn
        os.replace(partial, output)
    finally:
        partial.unlink(missing_ok=True)


def verify_output(output: Path, expected_seconds: float, expect_audio: bool) -> list[str]:
    from moviepy.video.io.ffmpeg_reader import ffmpeg_parse_infos

    info = ffmpeg_parse_infos(str(output))
    problems = []
    if tuple(info["video_size"]) != (WIDTH, HEIGHT):
        problems.append(f"size {info['video_size']} != {(WIDTH, HEIGHT)}")
    if abs(info["video_fps"] - FPS) > 0.01:
        problems.append(f"fps {info['video_fps']} != {FPS}")
    if abs(info["duration"] - expected_seconds) > 0.25:
        problems.append(f"duration {info['duration']:.2f}s != {expected_seconds:.2f}s")
    if bool(info.get("audio_found")) != expect_audio:
        problems.append(f"audio track present={bool(info.get('audio_found'))}, expected {expect_audio}")
    return problems


# ------------------------------------------------------------------------------------ command line

def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output .mp4 (default: %(default)s)")
    parser.add_argument("--font", type=Path, help=f"bold TTF to use (default: ${FONT_ENV}, else Arial Bold / Liberation Sans Bold / DejaVu Sans Bold)")
    parser.add_argument("--backdrop-dir", type=Path, help="folder holding act1..act4 footage; acts without a file stay on their solid colour")
    parser.add_argument("--music", type=Path, help="music bed (any format ffmpeg reads)")
    parser.add_argument("--voiceover", type=Path, help="60-second master voice-over; ducks the music under VOICEOVER_CUES")
    parser.add_argument("--preview", type=float, metavar="SECONDS", help="render only the first SECONDS (quick smoke test)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.preview is not None and not 0 < args.preview <= TOTAL_SECONDS:
            raise MediaInputError(f"--preview must be in (0, {TOTAL_SECONDS:g}] seconds")
        for flag, path in (("--music", args.music), ("--voiceover", args.voiceover)):
            if path is not None and not path.is_file():
                raise MediaInputError(f"{flag} file not found: {path}")
        if args.backdrop_dir is not None and not args.backdrop_dir.is_dir():
            raise MediaInputError(f"--backdrop-dir is not a directory: {args.backdrop_dir}")
        font = resolve_font(args.font)
        print(f"[SYS] Initializing {ENGINE_BANNER}...")
        video = build_video(font, args.backdrop_dir, args.music, args.voiceover)
    except MediaInputError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    missing = [n for n in range(1, len(ACTS) + 1) if find_backdrop(args.backdrop_dir, n) is None]
    if missing:
        print(f"[SYS] Solid-colour background for act(s) {', '.join(map(str, missing))} (no footage supplied).")
    has_audio = video.audio is not None
    if not has_audio:
        print("[WARN] No --music / --voiceover supplied: the render will be silent.")

    expected = args.preview or TOTAL_SECONDS
    print(f"[SYS] Rendering {expected:g}s at {WIDTH}x{HEIGHT} {FPS}fps -> {args.output}")
    render(video, args.output, args.preview)
    problems = verify_output(args.output, expected, has_audio)
    if problems:
        print("[FAIL] Output verification failed: " + "; ".join(problems), file=sys.stderr)
        return 1
    print(f"[SUCCESS] {args.output} ({args.output.stat().st_size:,} bytes, sha256 {sha256_of(args.output)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
