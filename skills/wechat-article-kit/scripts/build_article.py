#!/usr/bin/env python3
"""Generate a self-contained article with embedded images; no third-party dependencies."""
import argparse
import base64
import html
import json
import math
from pathlib import Path
import re
import sys

LIMIT = 10_000_000  # Project guardrail, not an official WeChat limit.
DEFAULTS = dict(body_font_size=16, heading_font_size=22, line_height=1.8,
                paragraph_gap=18, heading_gap=32, image_gap=8,
                content_width=680, side_padding=18, text_color="#30372d",
                accent_color="#344b2d", image_layout="columns")
RANGES = dict(body_font_size=(12, 28), heading_font_size=(16, 40),
              line_height=(1.2, 2.5), paragraph_gap=(0, 60),
              heading_gap=(0, 80), image_gap=(0, 40),
              content_width=(320, 960), side_padding=(0, 48))


def config(path):
    value = {} if path is None else json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("排版配置必须为 JSON 对象")
    unknown = set(value) - set(DEFAULTS)
    if unknown:
        raise ValueError("未知配置字段：" + ", ".join(sorted(unknown)))
    result = {**DEFAULTS, **value}
    for key, (low, high) in RANGES.items():
        n = result[key]
        if (isinstance(n, bool) or not isinstance(n, (int, float))
                or not math.isfinite(n) or not low <= n <= high):
            raise ValueError(f"{key} 必须在 {low}–{high} 之间")
    for key in ("text_color", "accent_color"):
        if not isinstance(result[key], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", result[key]):
            raise ValueError(f"{key} 必须为六位十六进制色号")
    if result["image_layout"] not in ("columns", "stacked"):
        raise ValueError("image_layout 必须为 columns 或 stacked")
    return result


def escaped(value):
    if not isinstance(value, str):
        raise ValueError("正文、标题、图片说明必须是文本")
    return html.escape(value, quote=True).replace("\n", "<br>")


def image_data(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("图片必须使用文章目录内的相对路径")
    path = (root / name).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        raise ValueError("图片不允许访问文章目录之外的文件") from None
    if not path.is_file():
        raise ValueError(f"找不到图片：{name}")
    if path.stat().st_size > LIMIT:
        raise ValueError(f"图片过大，请先压缩：{name}")
    data = path.read_bytes()
    if data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError(f"不支持的图片格式：{name}")
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def render(article_path, layout_path):
    article = json.loads(article_path.read_text(encoding="utf-8"))
    if not isinstance(article, dict):
        raise ValueError("文章必须为 JSON 对象")
    title = article.get("title", "我的图文")
    if not isinstance(title, str):
        raise ValueError("title 必须为文本")
    blocks = article.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("blocks 必须包含至少一个内容块")
    c = config(layout_path)
    items = []
    for block in blocks:
        if not isinstance(block, dict):
            raise ValueError("每个内容块必须为 JSON 对象")
        kind = block.get("type")
        if kind == "heading":
            items.append(f'<h2 style="font-size:{c["heading_font_size"]}px;'
                         f'line-height:1.5;color:{c["accent_color"]};'
                         f'margin:{c["heading_gap"]}px 0 12px;font-weight:600;">'
                         + escaped(block["text"]) + "</h2>")
        elif kind == "paragraph":
            items.append(f'<p style="font-size:{c["body_font_size"]}px;'
                         f'line-height:{c["line_height"]};margin:0 0 {c["paragraph_gap"]}px;">'
                         + escaped(block["text"]) + "</p>")
        elif kind == "images":
            files = block.get("files")
            if not isinstance(files, list) or not 1 <= len(files) <= 2:
                raise ValueError("每组图片必须为一或两张；更多图片请分组")
            alts = block.get("alts", [""] * len(files))
            if not isinstance(alts, list) or len(alts) != len(files):
                raise ValueError("alts 数量必须与 files 一致")
            mode = block.get("layout", c["image_layout"])
            if mode not in ("columns", "stacked"):
                raise ValueError("图片 layout 必须为 columns 或 stacked")
            parallel = len(files) == 2 and mode == "columns"
            style = (f'display:flex;gap:{c["image_gap"]}px;align-items:flex-start;'
                     if parallel else "display:block;")
            pics = []
            for name, alt in zip(files, alts):
                if not isinstance(alt, str):
                    raise ValueError("图片 alt 必须为文本")
                src = image_data(article_path.parent, name)
                wrapper = ("flex:1 1 0%;min-width:0;" if parallel
                           else f'margin-bottom:{c["image_gap"]}px;')
                pics.append(f'<div style="{wrapper}"><img src="{src}" '
                            f'alt="{html.escape(alt, quote=True)}" '
                            'style="display:block;width:100%;height:auto;border:0;"></div>')
            items.append(f'<section style="{style}margin:18px 0 {c["paragraph_gap"]}px;">'
                         + "".join(pics) + "</section>")
            if block.get("caption"):
                items.append('<p style="font-size:12px;line-height:1.7;color:#73786e;'
                             f'margin:0 0 {c["paragraph_gap"]}px;">'
                             + escaped(block["caption"]) + "</p>")
        else:
            raise ValueError(f"未知内容块类型：{kind}")
    body = (f'<section style="max-width:{c["content_width"]}px;margin:0 auto;'
            f'padding:18px {c["side_padding"]}px 36px;box-sizing:border-box;'
            'font-family:-apple-system,BlinkMacSystemFont,\'PingFang SC\','
            f'\'Microsoft YaHei\',Arial,sans-serif;background:#ffffff;color:{c["text_color"]};">'
            + "".join(items) + "</section>")
    if len(body.encode("utf-8")) >= LIMIT:
        raise ValueError("正文达到本工具的10 MB保护阈值；请压缩图片或分篇")
    template = (Path(__file__).resolve().parent.parent / "assets/template.html").read_text(encoding="utf-8")
    # Substitution must not interpret marker-like text from user articles.
    values = {"ARTICLE": body, "PAGE_TITLE": html.escape(title, quote=True)}
    return re.sub(r"\{\{(ARTICLE|PAGE_TITLE)\}\}",
                  lambda match: values[match.group(1)], template)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("article", type=Path)
    parser.add_argument("--layout", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true", help="明确覆盖现有输出")
    args = parser.parse_args()
    try:
        output = render(args.article.resolve(), args.layout)
        if args.output.resolve() in {args.article.resolve(), (args.layout or args.article).resolve()}:
            raise ValueError("输出路径不能覆盖输入文章或配置")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w" if args.overwrite else "x", encoding="utf-8") as stream:
            stream.write(output)
        print(f"已生成：{args.output}（{len(output.encode('utf-8')) / 1_000_000:.2f} MB）")
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"生成失败：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
