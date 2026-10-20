# Sentinel Apex 60-second corporate video

`generate_sentinel_apex_60s.py` renders the 60-second Vijayadashami / Dussehra mastercut (four 15-second acts, 1920x1080, 30 fps, H.264 + AAC) used for the Sentinel Apex and CYBERDUDEBIVASH ecosystem greeting. It is a marketing asset, not course content; it lives here only because this is where it was supplied.

## Run

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r scripts/media/requirements.txt
python scripts/media/generate_sentinel_apex_60s.py                 # dist/media/sentinel_apex_global_broadcast_60s.mp4 (git-ignored)
python scripts/media/generate_sentinel_apex_60s.py --preview 5     # 5-second smoke render
```

A full silent render takes about 1.5 minutes on one core. The script exits `0` only after it has re-read the finished file and confirmed size, frame rate, duration and audio presence; `2` means an input problem (nothing is written), `1` means the verification failed.

| Option | Effect |
|---|---|
| `--output FILE` | Where to write the `.mp4`. Written to a `.partial` file and moved into place only on success. |
| `--backdrop-dir DIR` | Looks for `act1` to `act4` (`.mp4`, `.mov`, `.webm`, `.mkv`). Footage is looped or trimmed to 15 s and scaled-to-cover; an act without a file keeps its solid colour. |
| `--music FILE` | Music bed, looped or trimmed to 60 s, 1.5 s fade-out, at -6 dB. |
| `--voiceover FILE` | Master voice-over placed at 0 s. With `--music`, the bed is ducked by 12.5 dB under the cues below, with a 0.25 s attack and 0.6 s release. |
| `--font FILE` | Bold TTF. Otherwise `$SENTINEL_APEX_FONT`, then Arial Bold, Liberation Sans Bold, DejaVu Sans Bold. |
| `--preview SECONDS` | Render only the first SECONDS. |

Without `--backdrop-dir`, `--music` and `--voiceover` the result is **text on solid colours with no audio**; the script says so on every run.

## Design decisions

- **Flat timeline.** Every layer carries its own absolute start time and one composite sets the 60.0 s duration. (The first draft nested each act in its own composite and shifted it twice, which produced a 105 s video with the acts at 0, 30, 60 and 90 s.)
- **Pillow text, not ImageMagick.** moviepy's `TextClip` needs ImageMagick, whose default security policy blocks the `@file` input it uses, and a font *name* the OS may not know. Text is rasterised with Pillow from a TTF file instead, so the render needs only the pinned Python packages (ffmpeg ships inside `imageio-ffmpeg`).
- **Title-safe by construction.** Text is centred in an 80 % x 80 % box. A copy edit that overflows the box fails the render rather than being clipped.
- **Pinned moviepy 1.0.3.** moviepy 2.x removed `moviepy.editor`. Backdrop scaling uses Pillow directly because moviepy 1.0.3's own `resize` calls `Image.ANTIALIAS`, which Pillow 10+ removed.
- **16:9 only.** There is no 9:16 or 1:1 export yet.

## Production inputs

### Backdrop footage prompts (generate with a video model, save as `act1` to `act4`)

1. Act 1, 0 to 15 s: "Ultra-premium corporate motion graphics, 4K resolution, cinematic moody lighting. Deep dark obsidian hyper-secure digital network matrix structure pulsing under intense crimson structural threat indicators. A brilliant golden arrow of raw energetic power blasts from the foreground, fracturing the anomalies, settling into a heavy metallic dark gray emblem base right in the center. Impeccable industrial security aesthetic, high-contrast, clean 60fps."
2. Act 2, 15 to 30 s: "Sleek, enterprise-grade AI server room architectural interior, electric cyan light ribbons cutting through high-polished chrome and gunmetal surfaces. A massive, gleaming holographic fortress shield engine locks perfectly into the dead center of the screen, emanating waves of protective computing power. Ultra-clear, hyper-realistic, high contrast commercial rendering."
3. Act 3, 30 to 45 s: "Global threat intelligence response command center, abstract minimalist node networks and global data packets tracking cleanly over an dark global grid projection map. Subtle white light beams pulse outward from the frame's core center. Sophisticated corporate architecture, maximum visibility, depth-of-field, sharp details."
4. Act 4, 45 to 60 s: "Luxury global enterprise corporate boardroom skyscraper interior overlooking a blurred modern financial district skyline. Floating slowly through the peripheral safe zones are hyper-realistic 3D golden marigold petals and elegant, clean digital diya flames glowing with steady amber light waves. The center 70% viewing space is held perfectly clear, deep, and high-contrast dark for absolute maximum typographic visibility."

The renderer does not darken footage. Keep the centre of each clip dark enough for the white, cyan and gold text (the prompts ask for this); check a frame from each act before publishing.

### Voice-over script (cues are `VOICEOVER_CUES` in the script)

| Cue | Delivery | Line |
|---|---|---|
| 00:02 to 00:12 | Deep, resonant, crystal-clear | "In an era of hyper-scale digital complexity, absolute resilience isn't just an asset... it is a global enterprise mandate. Welcome to the Sentinel Apex Brand." |
| 00:17 to 00:27 | Dynamic pace, crisp definition | "Introducing the apex of corporate cyber defense. Where global enterprise security meets completely autonomous execution. This is the Sentinel Apex AI Security Hub." |
| 00:32 to 00:42 | Deep, authoritative | "Powering real-time global intelligence pipelines, rapid mitigation automation, and compliance gap analysis across the Fortune 500 footprint." |

Act 4 (45 to 60 s) is music only. The voice-over audio itself is not generated here: record it or produce it with an approved text-to-speech service and pass it with `--voiceover`.

## Tests

```bash
pip install -r scripts/media/requirements.txt pytest==9.1.1
pytest tests/test_sentinel_apex_video.py
```

The suite checks the 60 s timeline and act boundaries, title-safe centring, WCAG AAA text contrast, the exact -12.5 dB ducking depth (measured in the encoded audio), backdrop looping and cropping, and the input-error exit codes. Tests that need the media packages are skipped when those are not installed, which is the case for the manual `validate-repository` workflow, which does not install them.
