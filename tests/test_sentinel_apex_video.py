"""Sentinel Apex 60 s video generator: timeline, title-safe layout, contrast, music ducking and end-to-end renders.

Pure-logic tests run anywhere. Tests that need moviepy / Pillow / numpy skip when the optional media toolchain
(scripts/media/requirements.txt) is not installed.
"""
from __future__ import annotations

import subprocess
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "media"))
import check_contrast
import generate_sentinel_apex_60s as gen

CANONICAL_HOSTS = ("www.cyberdudebivash.in", "intel.cyberdudebivash.com", "www.cyberdudebivash.com")


class FakeFont:
    """10 px per character, so wrapping can be asserted without a font file."""

    def getlength(self, text: str) -> float:
        return 10.0 * len(text)


@pytest.fixture(scope="module")
def np():
    return pytest.importorskip("numpy")


@pytest.fixture(scope="module")
def font_path():
    pytest.importorskip("PIL")
    try:
        return gen.resolve_font()
    except gen.MediaInputError:
        pytest.skip("no bold sans-serif font installed")


@pytest.fixture(scope="module")
def video(np, font_path):
    pytest.importorskip("moviepy.editor")
    return gen.build_video(font_path)


def write_wav(path: Path, samples, rate: int = 44100) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples.astype("<i2").tobytes())


# ------------------------------------------------------------------------------------ copy, contrast, timeline

def test_timeline_is_four_15_second_acts_totalling_60_seconds():
    assert len(gen.ACTS) == 4
    assert gen.ACT_SECONDS == 15.0 and gen.TOTAL_SECONDS == 60.0


def test_every_act_text_meets_wcag_aaa_contrast_on_its_background():
    for act in gen.ACTS:
        background = "#{:02x}{:02x}{:02x}".format(*act.background)
        assert check_contrast.contrast(act.color, background) >= 7.0, act.name


def test_copy_carries_the_three_canonical_domains_exactly():
    copy = "\n".join(act.text for act in gen.ACTS)
    for host in CANONICAL_HOSTS:
        assert host in copy


def test_festive_greeting_addresses_production_customers_not_the_fortune_500():
    greeting = gen.ACTS[-1].text.replace("\n", " ")
    assert "WISHING THE PRODUCTION CUSTOMERS A PROSPEROUS DUSSEHRA" in greeting
    assert "FORTUNE 500" not in "\n".join(act.text.upper() for act in gen.ACTS)


def test_wrap_text_keeps_paragraph_breaks_and_respects_the_width():
    assert gen.wrap_text("aaaa bbbb cccc\n\nz", FakeFont(), 90) == ["aaaa bbbb", "cccc", "", "z"]


def test_resolve_font_rejects_a_missing_explicit_font(tmp_path):
    with pytest.raises(gen.MediaInputError):
        gen.resolve_font(tmp_path / "absent.ttf")


def test_resolve_font_honours_the_environment_override(tmp_path, monkeypatch):
    font = tmp_path / "custom.ttf"
    font.write_bytes(b"not parsed here")
    monkeypatch.setenv(gen.FONT_ENV, str(font))
    assert gen.resolve_font() == font


# ------------------------------------------------------------------------------------ music ducking

def test_duck_gain_is_minus_12_5_db_under_every_cue_and_unity_elsewhere(np):
    inside = gen.duck_gain(np.array([2.0, 7.0, 12.0, 17.0, 22.0, 27.0, 32.0, 42.0]))
    assert 20 * np.log10(inside) == pytest.approx(-12.5)
    assert gen.duck_gain(np.array([0.0, 14.0, 29.0, 44.0, 59.9])) == pytest.approx(1.0)
    assert float(gen.duck_gain(7.0)) == pytest.approx(10 ** (-12.5 / 20))      # scalar time works too


def test_duck_gain_ramps_without_jumps_and_stays_in_range(np):
    gains = gen.duck_gain(np.linspace(0, 60, 6001))
    floor = 10 ** (gen.DUCK_DB / 20)
    assert gains.min() == pytest.approx(floor) and gains.max() == pytest.approx(1.0)
    assert np.abs(np.diff(gains)).max() < 0.04          # 10 ms step; the steepest ramp (attack) moves ~0.03 per step


# ------------------------------------------------------------------------------------ title-safe text

def test_every_act_fits_the_title_safe_box_and_is_horizontally_centred(np, font_path):
    box = int(gen.WIDTH * gen.SAFE_RATIO)
    for act in gen.ACTS:
        card = gen.render_text_card(act.text, font_path, act.font_size, act.color, box)
        assert card.shape[1] == box and card.shape[0] <= gen.HEIGHT * gen.SAFE_RATIO, act.name
        columns = np.where(card[:, :, 3].any(axis=0))[0]
        assert abs((columns.min() + columns.max()) / 2 - box / 2) < 4, act.name


def test_a_word_wider_than_the_safe_box_is_rejected_not_clipped(font_path):
    with pytest.raises(gen.MediaInputError):
        gen.render_text_card("W" * 200, font_path, 62, "#FFFFFF", int(gen.WIDTH * gen.SAFE_RATIO))


# ------------------------------------------------------------------------------------ composed timeline (moviepy)

def test_video_is_exactly_60_seconds_of_1080p(video):
    assert video.duration == 60.0
    assert tuple(video.size) == (1920, 1080)


def test_each_act_appears_at_its_own_time_with_text_locked_to_the_centre(np, video):
    margin = int(gen.WIDTH * (1 - gen.SAFE_RATIO) / 2)
    for index, act in enumerate(gen.ACTS):
        frame = video.get_frame(index * gen.ACT_SECONDS + 7.5)
        background = np.array(act.background)
        assert (frame[:, :margin] == background).all() and (frame[:, -margin:] == background).all(), act.name   # nothing outside the safe box
        inked = (frame != background).any(axis=2)
        rows, columns = np.where(inked.any(axis=1))[0], np.where(inked.any(axis=0))[0]
        assert abs((columns.min() + columns.max()) / 2 - gen.WIDTH / 2) < 4, act.name
        assert abs((rows.min() + rows.max()) / 2 - gen.HEIGHT / 2) < 25, act.name


def test_acts_switch_exactly_on_the_15_second_boundaries(np, video):
    for boundary in (15.0, 30.0, 45.0):
        before, after = int(boundary // gen.ACT_SECONDS) - 1, int(boundary // gen.ACT_SECONDS)
        assert tuple(video.get_frame(boundary - 0.05)[5, 5]) == gen.ACTS[before].background
        assert tuple(video.get_frame(boundary + 0.05)[5, 5]) == gen.ACTS[after].background


def test_text_fades_in_from_the_background(np, video):
    for index, act in enumerate(gen.ACTS):
        assert (video.get_frame(index * gen.ACT_SECONDS) == np.array(act.background)).all()


# ------------------------------------------------------------------------------------ command line and end-to-end renders

@pytest.mark.parametrize("flag", ["--music", "--voiceover"])
def test_missing_audio_input_is_a_usage_error_and_creates_nothing(tmp_path, flag):
    output = tmp_path / "out.mp4"
    assert gen.main(["--output", str(output), flag, str(tmp_path / "absent.wav")]) == 2
    assert not output.exists() and not list(tmp_path.iterdir())


@pytest.mark.parametrize("seconds", ["0", "60.5", "-1"])
def test_preview_length_outside_the_timeline_is_a_usage_error(tmp_path, seconds):
    assert gen.main(["--output", str(tmp_path / "out.mp4"), f"--preview={seconds}"]) == 2


def test_preview_render_is_a_verified_silent_1080p_mp4_with_no_partial_file(tmp_path, video):
    output = tmp_path / "preview.mp4"
    assert gen.main(["--output", str(output), "--preview", "2"]) == 0
    assert [p.name for p in tmp_path.iterdir()] == ["preview.mp4"]
    assert gen.verify_output(output, 2.0, expect_audio=False) == []
    assert gen.verify_output(output, 60.0, expect_audio=True) != []        # the verifier can actually fail


def test_music_is_ducked_12_5_db_under_the_voiceover_in_the_rendered_file(np, tmp_path, video):
    music = tmp_path / "music.wav"
    voice = tmp_path / "voice.wav"
    t = np.arange(44100 * 6) / 44100
    write_wav(music, 8000 * np.sin(2 * np.pi * 440 * t))
    write_wav(voice, np.zeros(44100 * 6))                                    # silent voice-over: the mix is the ducked bed alone
    output = tmp_path / "mix.mp4"
    assert gen.main(["--output", str(output), "--music", str(music), "--voiceover", str(voice), "--preview", "4"]) == 0
    assert gen.verify_output(output, 4.0, expect_audio=True) == []

    import imageio_ffmpeg
    pcm = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", str(output), "-vn", "-ac", "1", "-ar", "44100", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    samples = np.frombuffer(pcm, dtype="<i2").astype(float)

    def rms(start: float, end: float) -> float:
        window = samples[int(start * 44100):int(end * 44100)]
        return float(np.sqrt(np.mean(window ** 2)))

    bed, ducked = rms(0.3, 1.5), rms(2.5, 3.9)                               # cue 1 starts at 2.0 s, ramp-down ends there
    assert bed > 1000
    assert ducked / bed == pytest.approx(10 ** (gen.DUCK_DB / 20), rel=0.12)


def test_backdrop_footage_is_looped_cover_scaled_and_only_replaces_its_own_act(np, tmp_path, font_path):
    mp = pytest.importorskip("moviepy.editor")
    footage_dir = tmp_path / "footage"
    footage_dir.mkdir()
    red = (200, 30, 30)
    mp.ColorClip(size=(400, 200), color=red, duration=1.0).write_videofile(                 # 2:1 footage: must be cropped, not stretched or letter-boxed
        str(footage_dir / "act1.mp4"), fps=10, codec="libx264", logger=None, ffmpeg_params=["-pix_fmt", "yuv420p"])
    composed = gen.build_video(font_path, backdrop_dir=footage_dir)
    for t in (0.0, 10.0, 14.0):                                                              # 1 s of footage must loop to cover the whole 15 s act
        frame = composed.get_frame(t)
        assert frame.shape == (gen.HEIGHT, gen.WIDTH, 3)
        assert np.abs(frame[5, 5].astype(int) - red).max() <= 12, t                          # H.264 colour round-trip tolerance
    assert tuple(composed.get_frame(20.0)[5, 5]) == gen.ACTS[1].background
