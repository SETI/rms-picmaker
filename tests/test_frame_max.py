"""--frame_max regression test — output dims must not exceed `frame_max%` of frame."""

from pathlib import Path

from PIL import Image

from picmaker import images_to_pics


def test_frame_max_caps_at_half_frame(fixtures_dir: Path, tmp_path: Path) -> None:
    # 16x16 input + frame 512x512 + frame_max=50: the legacy `get_size`
    # interprets frame_max as "max % of the input dimensions that the output
    # may use," so the 16x16 input scales to 50% = 8x8 instead of filling
    # the 512x512 frame.
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        frame=(512, 512),
        frame_max=50,
    )
    out = tmp_path / 'cassini_iss.jpg'
    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (8, 8)
