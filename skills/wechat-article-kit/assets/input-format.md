# 输入格式

文章文件与 images 文件夹放在一起。图片路径相对于文章 JSON，必须处于该目录或子目录。仅支持 JPEG、PNG、WebP；不接受网络地址或目录外文件。

```json
{
  "title": "我的文章",
  "blocks": [
    {"type": "paragraph", "text": "文章导语。\n这里是换行。"},
    {"type": "heading", "text": "第一个小节"},
    {"type": "images", "files": ["images/01.jpg", "images/02.jpg"], "alts": ["图片一", "图片二"], "layout": "columns", "caption": "图片说明与来源"},
    {"type": "paragraph", "text": "正文"}
  ]
}
```

- `title` 用于浏览器标签，不自动放入正文；需要正文大标题时添加 heading。
- `paragraph`、`heading`：`text` 为普通文本，HTML 字符自动转义。
- `images`：`files` 一到两个；`alts` 可省略，提供时数量必须与 files 一致；`caption` 可省略；`layout` 为 `columns` 或 `stacked`，省略则用配置。
- 单图总是独占一行。图文顺序与 blocks 顺序一致。纯文字、零图及多组图都支持。
- 不传入 HTML、脚本、公众号密码或 API 密钥。

配置支持下列字段；省略时使用默认值：

```json
{
  "body_font_size": 16,
  "heading_font_size": 22,
  "line_height": 1.8,
  "paragraph_gap": 18,
  "heading_gap": 32,
  "image_gap": 8,
  "content_width": 680,
  "side_padding": 18,
  "text_color": "#30372d",
  "accent_color": "#344b2d",
  "image_layout": "columns"
}
```

长度单位为 px，line_height 为倍数。颜色只接受六位十六进制色号。不保存品牌身份、账号信息或个人路径。
