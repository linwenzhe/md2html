#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2html.py —— 通过 JSON 配置把 Markdown 转成 HTML。

支持 4 种图片处理模式:
    1  不展示图片
    2  引用图片 (需配置 image_root + html_image_base)
    3  data.js 方式
    4  Base64 内嵌 (默认)

用法:
    python md2html.py config.json
    python md2html.py config.json --image-mode 4
    python md2html.py config.json --help-modes

依赖:
    pip install markdown pygments
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from string import Template
from typing import Any
from urllib.parse import unquote

try:
    import markdown
except ImportError:
    sys.exit("缺少依赖，请先执行:  pip install markdown pygments")

try:
    import pygments  # noqa: F401
    from pygments.formatters import HtmlFormatter

    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False


# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
IMG_NONE = 1
IMG_REFERENCE = 2
IMG_DATA_JS = 3
IMG_BASE64 = 4

MODE_ALIAS = {
    "none": IMG_NONE, "no": IMG_NONE, "hide": IMG_NONE,
    "reference": IMG_REFERENCE, "ref": IMG_REFERENCE, "link": IMG_REFERENCE,
    "datajs": IMG_DATA_JS, "data_js": IMG_DATA_JS, "js": IMG_DATA_JS,
    "base64": IMG_BASE64, "inline": IMG_BASE64, "embed": IMG_BASE64,
}

DOC_FIELDS = ("说明", "_comment", "description", "注释", "remark")

IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc=")([^"]+)(")', re.IGNORECASE)
IMG_TAG_RE = re.compile(r"<img\b[^>]*?>", re.IGNORECASE)
PLACEHOLDER_GIF = "data:image/gif;base64,R0lGODlhAQABAAAAACw="


# --------------------------------------------------------------------------- #
# 页面模板
# --------------------------------------------------------------------------- #
PAGE_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>
$pygments_css
:root { color-scheme: light; }
body {
  max-width: 860px; margin: 0 auto; padding: 2rem 1.25rem 6rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  line-height: 1.75; color: #24292f; word-wrap: break-word;
}
h1, h2, h3, h4 { line-height: 1.3; margin-top: 1.6em; }
h1 { border-bottom: 1px solid #d0d7de; padding-bottom: .3em; }
h2 { border-bottom: 1px solid #eaeef2; padding-bottom: .3em; }
a { color: #0969da; }
pre { background: #f6f8fa; padding: 1rem 1.2rem; border-radius: 6px;
      overflow-x: auto; font-size: .875em; line-height: 1.5; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
:not(pre) > code { background: rgba(27,31,35,.06); padding: .2em .4em;
                   border-radius: 4px; font-size: .875em; }
blockquote { margin: 0; padding: 0 1em; color: #57606a;
             border-left: .25em solid #d0d7de; }
table { border-collapse: collapse; display: block; overflow-x: auto; }
th, td { border: 1px solid #d0d7de; padding: .4em .8em; }
th { background: #f6f8fa; }
img { max-width: 100%; }
hr { border: 0; border-top: 1px solid #d0d7de; margin: 2rem 0; }
.toc { background: #f6f8fa; border-radius: 6px; padding: 1rem 1.5rem;
       margin-bottom: 2rem; }
.toc > ul { padding-left: 1.2rem; }
.toc li { margin: .15rem 0; }
</style>
</head>
<body>
$toc
$content
$extra_body
</body>
</html>
"""
)


# --------------------------------------------------------------------------- #
# 通用工具
# --------------------------------------------------------------------------- #
def strip_doc_fields(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in DOC_FIELDS}


def get_mode_help(cfg: dict, mode: Any = None) -> str:
    doc = cfg.get("说明") or cfg.get("description") or {}
    modes = doc.get("image_mode") if isinstance(doc, dict) else None
    if not isinstance(modes, dict):
        return ""
    if mode is None:
        lines = [f"  {k}: {v}" for k, v in sorted(modes.items())]
        return "image_mode 可选值：\n" + "\n".join(lines)
    return f"  image_mode={mode}: {modes.get(str(mode), '(未在说明中定义)')}"


def resolve_mode(raw: Any) -> int | None:
    if isinstance(raw, str):
        low = raw.strip().lower()
        if low in MODE_ALIAS:
            return MODE_ALIAS[low]
        try:
            return int(low)
        except ValueError:
            return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def resolve_path(base_dir: Path, p: str | Path) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (base_dir / path).resolve()


# --------------------------------------------------------------------------- #
# Markdown 渲染
# --------------------------------------------------------------------------- #
def pygments_css(css_class: str = "highlight") -> str:
    if not HAS_PYGMENTS:
        return ""
    return HtmlFormatter(style="default").get_style_defs(f".{css_class}")


def render(text: str, *, toc: bool, highlight: bool, toc_depth: str = "2-4"):
    extensions = ["extra", "sane_lists", "toc"]
    configs: dict[str, Any] = {"toc": {"toc_depth": toc_depth, "permalink": False}}
    if highlight and HAS_PYGMENTS:
        extensions.append("codehilite")
        configs["codehilite"] = {
            "guess_lang": False, "css_class": "highlight", "linenums": False,
        }
    md = markdown.Markdown(
        extensions=extensions, extension_configs=configs, output_format="html"
    )
    content = md.convert(text)
    return content, (md.toc if toc else "")


# --------------------------------------------------------------------------- #
# 图片资源工具
# --------------------------------------------------------------------------- #
def _is_remote(src: str) -> bool:
    return src.startswith(("http://", "https://", "data:", "//", "mailto:"))


def _clean_src(src: str) -> str:
    return unquote(src.split("#")[0].split("?")[0])


def _to_data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


# --------------------------------------------------------------------------- #
# 4 种图片模式
# --------------------------------------------------------------------------- #
def mode_none(html_text: str) -> str:
    """模式 1：删除所有 <img> 标签。"""
    return IMG_TAG_RE.sub("", html_text)


def mode_reference(
    html_text: str, image_root: Path | None, html_image_base: str
) -> str:
    """模式 2：改写 src 为 html_image_base + 原路径。"""
    base = html_image_base.rstrip("/")

    def repl(m: re.Match) -> str:
        prefix, src, suffix = m.group(1), m.group(2), m.group(3)
        if _is_remote(src):
            return m.group(0)

        clean = _clean_src(src).lstrip("/")

        if image_root is not None:
            disk = image_root / clean
            if not disk.is_file():
                print(f"⚠️  图片不存在: {disk}", file=sys.stderr)

        new_src = f"{base}/{clean}" if base else clean
        return f"{prefix}{new_src}{suffix}"

    return IMG_SRC_RE.sub(repl, html_text)


def mode_data_js(html_text: str, base_dir: Path):
    """模式 3：src 换成占位图 + data-md-asset 标记。"""
    assets: dict[str, str] = {}

    def repl(m: re.Match) -> str:
        prefix, src, suffix = m.group(1), m.group(2), m.group(3)
        if _is_remote(src):
            return m.group(0)

        clean = _clean_src(src)
        disk = Path(clean)
        if not disk.is_absolute():
            disk = (base_dir / disk).resolve()

        if not disk.is_file():
            print(f"⚠️  图片不存在: {disk}", file=sys.stderr)
            return m.group(0)

        if clean not in assets:
            assets[clean] = _to_data_uri(disk)

        return (
            f'{prefix}{PLACEHOLDER_GIF}" '
            f'data-md-asset="{html.escape(clean)}"{suffix}'
        )

    new_html = IMG_SRC_RE.sub(repl, html_text)
    return new_html, assets


def mode_base64(html_text: str, base_dir: Path) -> str:
    """模式 4：直接内嵌 base64。"""
    cache: dict[str, str] = {}

    def repl(m: re.Match) -> str:
        prefix, src, suffix = m.group(1), m.group(2), m.group(3)
        if _is_remote(src):
            return m.group(0)

        clean = _clean_src(src)
        disk = Path(clean)
        if not disk.is_absolute():
            disk = (base_dir / disk).resolve()

        if not disk.is_file():
            print(f"⚠️  图片不存在: {disk}", file=sys.stderr)
            return m.group(0)

        if clean not in cache:
            cache[clean] = _to_data_uri(disk)
        return f"{prefix}{cache[clean]}{suffix}"

    return IMG_SRC_RE.sub(repl, html_text)


def make_data_js(assets: dict[str, str]) -> str:
    payload = json.dumps(assets, ensure_ascii=False)
    return (
        f"window.__MD_ASSETS__ = {payload};\n"
        "(function(){\n"
        "  var nodes = document.querySelectorAll('[data-md-asset]');\n"
        "  for (var i=0;i<nodes.length;i++){\n"
        "    var el = nodes[i];\n"
        "    var key = el.getAttribute('data-md-asset');\n"
        "    var uri = window.__MD_ASSETS__[key];\n"
        "    if (uri) el.src = uri;\n"
        "  }\n"
        "})();\n"
    )


# --------------------------------------------------------------------------- #
# 单个任务
# --------------------------------------------------------------------------- #
def convert_one(job: dict, defaults: dict, base_dir: Path) -> tuple[bool, str]:
    raw = {**defaults, **job}          # 保留说明，用于报错
    p = strip_doc_fields(raw)          # 参数视图

    input_str = p.get("input")
    if not input_str:
        return False, "配置缺少 'input' 字段"

    src = resolve_path(base_dir, input_str)
    if not src.is_file():
        return False, f"找不到输入文件: {src}"

    # 输出路径
    if p.get("output"):
        out = resolve_path(base_dir, p["output"])
    elif p.get("output_dir"):
        out_dir = resolve_path(base_dir, p["output_dir"])
        out = out_dir / src.with_suffix(".html").name
    else:
        out = src.with_suffix(".html")

    # 通用参数
    title = p.get("title") or src.stem
    toc = bool(p.get("toc", False))
    toc_depth = str(p.get("toc_depth", "2-4"))
    highlight = bool(p.get("highlight", True))
    fragment = bool(p.get("fragment", False))

    raw_mode = p.get("image_mode", IMG_BASE64)
    image_mode = resolve_mode(raw_mode)
    if image_mode not in (1, 2, 3, 4):
        hint = get_mode_help(raw, raw_mode)
        return False, f"未知的 image_mode: {raw_mode!r}\n{hint}"

    # 渲染 Markdown
    text = src.read_text(encoding="utf-8")
    content, toc_html = render(
        text, toc=toc, highlight=highlight, toc_depth=toc_depth
    )

    # 图片处理
    data_js_tag = ""

    if image_mode == IMG_NONE:
        content = mode_none(content)

    elif image_mode == IMG_REFERENCE:
        image_root = (
            resolve_path(base_dir, p["image_root"]) if p.get("image_root") else None
        )
        html_image_base = str(p.get("html_image_base", ""))
        content = mode_reference(content, image_root, html_image_base)

    elif image_mode == IMG_DATA_JS:
        content, assets = mode_data_js(content, src.parent)

        dj_raw = p.get("data_js_output")
        dj_path = resolve_path(base_dir, dj_raw) if dj_raw \
            else (out.parent / "data.js")

        try:
            rel = Path(os.path.relpath(dj_path, out.parent)).as_posix()
        except ValueError:
            rel = dj_path.as_posix()

        data_js_tag = f'<script src="{html.escape(rel)}"></script>'

        dj_path.parent.mkdir(parents=True, exist_ok=True)
        dj_path.write_text(make_data_js(assets), encoding="utf-8")
        print(f"   ↳ 已写出 {dj_path}", file=sys.stderr)

    else:  # IMG_BASE64
        content = mode_base64(content, src.parent)

    # 组装
    if fragment:
        output = f"{toc_html}\n{content}" if toc_html else content
    else:
        output = PAGE_TEMPLATE.substitute(
            title=html.escape(title),
            toc=toc_html,
            content=content,
            pygments_css=pygments_css(),
            extra_body=data_js_tag,
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output, encoding="utf-8")
    return True, f"{src}  ->  {out}"


# --------------------------------------------------------------------------- #
# 配置加载
# --------------------------------------------------------------------------- #
def load_jobs(cfg: dict) -> tuple[dict, list[dict]]:
    defaults = cfg.get("defaults", {})
    if "jobs" in cfg:
        jobs = cfg["jobs"]
        if not isinstance(jobs, list) or not jobs:
            raise ValueError("'jobs' 必须是非空数组")
        return defaults, jobs

    single = {k: v for k, v in cfg.items() if k not in ("defaults", "jobs")}
    if "input" not in single:
        raise ValueError("配置里既没有 'jobs'，也没有顶层 'input'")
    return defaults, [single]


# --------------------------------------------------------------------------- #
# 命令行
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="md2html",
        description="通过 JSON 配置把 Markdown 转成 HTML。",
    )
    p.add_argument("config", help="JSON 配置文件路径")
    p.add_argument("--help-modes", action="store_true",
                   help="打印配置里 image_mode 的说明并退出")
    p.add_argument("--image-mode", type=str,
                   help="覆盖 image_mode（支持 1-4 或别名 none/reference/datajs/base64）")
    p.add_argument("--input")
    p.add_argument("--output")
    p.add_argument("--title")
    p.add_argument("--toc", action="store_true")
    p.add_argument("--no-highlight", action="store_true")
    p.add_argument("--fragment", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(f"错误：找不到配置文件 {cfg_path}", file=sys.stderr)
        return 1

    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"错误：JSON 解析失败 —— {e}", file=sys.stderr)
        return 1

    if args.help_modes:
        print(get_mode_help(cfg) or "配置里没有 '说明.image_mode' 字段。")
        return 0

    try:
        defaults, jobs = load_jobs(cfg)
    except ValueError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1

    overrides: dict[str, Any] = {}
    if args.image_mode:
        overrides["image_mode"] = args.image_mode
    if args.input:
        overrides["input"] = args.input
    if args.output:
        overrides["output"] = args.output
    if args.title:
        overrides["title"] = args.title
    if args.toc:
        overrides["toc"] = True
    if args.no_highlight:
        overrides["highlight"] = False
    if args.fragment:
        overrides["fragment"] = True

    if overrides:
        if len(jobs) > 1:
            print("提示：批量模式下忽略命令行覆盖参数", file=sys.stderr)
        else:
            jobs = [{**jobs[0], **overrides}]

    base_dir = cfg_path.parent.resolve()

    failed = 0
    for i, job in enumerate(jobs, 1):
        ok, msg = convert_one(job, defaults, base_dir)
        print(f"{'✅' if ok else '❌'} [{i}/{len(jobs)}] {msg}", file=sys.stderr)
        if not ok:
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())