"""Run: python3 -m unittest discover -s tests -v"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/wechat-article-kit/scripts/build_article.py"
spec = importlib.util.spec_from_file_location("builder", SCRIPT)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.input = self.root / "article.json"
        (self.root / "photo.jpg").write_bytes((ROOT / "examples/images/01.jpg").read_bytes())

    def tearDown(self):
        self.temp.cleanup()

    def article(self, blocks):
        self.input.write_text(json.dumps({"title": "测试", "blocks": blocks}), encoding="utf-8")
        return builder.render(self.input, None)

    def test_plain_text_escape_and_literal_markers(self):
        output = self.article([{"type": "paragraph", "text": '<script>alert(1)</script> {{PAGE_TITLE}}'}])
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt; {{PAGE_TITLE}}', output)
        self.assertNotIn('<script>alert(1)</script>', output)

    def test_zero_one_and_seven_images(self):
        for count in (0, 1, 7):
            blocks = [{"type": "paragraph", "text": "正文"}]
            blocks += [{"type": "images", "files": ["photo.jpg"]} for _ in range(count)]
            output = self.article(blocks)
            self.assertEqual(output.count('<img src="data:image/jpeg;base64,'), count)

    def test_missing_image_fails(self):
        with self.assertRaisesRegex(ValueError, "找不到图片"):
            self.article([{"type": "images", "files": ["missing.jpg"]}])

    def test_parent_path_and_symlink_escape_fail(self):
        with self.assertRaisesRegex(ValueError, "之外"):
            self.article([{"type": "images", "files": ["../outside.jpg"]}])
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / "secret.jpg"
            target.write_bytes((self.root / "photo.jpg").read_bytes())
            (self.root / "link.jpg").symlink_to(target)
            with self.assertRaisesRegex(ValueError, "之外"):
                self.article([{"type": "images", "files": ["link.jpg"]}])

    def test_remote_image_fails(self):
        with self.assertRaises(ValueError):
            self.article([{"type": "images", "files": ["https://example.org/photo.jpg"]}])

    def test_non_image_fails(self):
        (self.root / "fake.jpg").write_text("<script>bad()</script>")
        with self.assertRaisesRegex(ValueError, "格式"):
            self.article([{"type": "images", "files": ["fake.jpg"]}])

    def test_oversized_body_fails(self):
        with self.assertRaisesRegex(ValueError, "保护阈值"):
            self.article([{"type": "paragraph", "text": "文" * 3_400_000}])

    def test_style_injection_and_unknown_config_fail(self):
        layout = self.root / "layout.json"
        for value in ({"text_color": "red;display:none"}, {"unknown": 1},
                      {"body_font_size": True}, {"line_height": 99}):
            layout.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                builder.config(layout)

    def test_cli_does_not_overwrite_existing_output(self):
        self.article([{"type": "paragraph", "text": "正文"}])
        out = self.root / "out.html"
        out.write_text("keep me")
        run = subprocess.run([sys.executable, str(SCRIPT), str(self.input),
                              "--output", str(out)], capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(out.read_text(), "keep me")


if __name__ == "__main__":
    unittest.main()
