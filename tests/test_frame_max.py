"""--frame_max regression test — output dims must not exceed `frame_max%` of frame."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from picmaker.picmaker import images_to_pics


def test_frame_max_caps_at_half_frame(fixtures_dir: Path, tmp_path: Path) -> None:
    # 16x16 input + frame 512x512 + frame_max=50% → ≤ 256x256.
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        frame=(512, 512),
        frame_max=50,
    )
    out = tmp_path / 'cassini_iss.jpg'
    assert out.exists()
    with Image.open(out) as img:
        assert max(img.size) <= 256
