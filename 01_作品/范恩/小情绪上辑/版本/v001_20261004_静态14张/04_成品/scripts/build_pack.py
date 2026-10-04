#!/usr/bin/env python3
"""Build one 8-to-24-item static pack from original transparent, text-free artwork."""
from pathlib import Path
import argparse
import copy
import csv
import html
import json
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

from pack_utils import (PROFILE, dump, find_font, fit_art, outline, read_alpha,
                        resize_alpha, save_gif, save_opaque, save_png, sha, text_layer, font_index,
                        caption_typography)


def validate_job(job, base):
    if not isinstance(job.get("title"), str) or not job["title"].strip():
        raise ValueError("job.title 必须为非空专辑名")
    characters = job.get("characters", [])
    if not isinstance(characters, list) or len(characters) != 1 or not isinstance(characters[0], str) or not characters[0].strip():
        raise ValueError("job.characters 必须且只能包含 1 只猫的名字；缺失或多个猫名不生成素材。")
    items = job.get("items", [])
    if not 8 <= len(items) <= 24 or job.get("count", len(items)) != len(items):
        raise ValueError(f"每个 job 必须为8至24条且count一致，当前为{len(items)}")
    meanings = []
    paths = []
    for i, item in enumerate(items, 1):
        if not isinstance(item.get("caption"), str) or not item["caption"].strip() or "\n" in item["caption"]:
            raise ValueError(f"第{i}条 caption 须为非空单行原文")
        meaning = item.get("meaning", "")
        if not isinstance(meaning, str) or not 1 <= len(meaning) <= 4 or not meaning.strip():
            raise ValueError(f"第{i}条 meaning 须为1至4字的含义词")
        meanings.append(meaning)
        cast = item.get("characters", [])
        if not cast or len(set(cast)) != len(cast) or not set(cast) <= set(characters):
            raise ValueError(f"第{i}条 characters 须为已声明角色的非空不重复子集")
        if not isinstance(item.get("art"), str):
            raise ValueError(f"第{i}条缺少原画 art 路径；先生成原画再导出")
        paths.append((f"items[{i}].art", base / item["art"]))
    if len(set(meanings)) != len(items):
        raise ValueError("全部 meaning 须唯一；不能自动截断文案产生重复")
    extras = job.get("extras", {})
    for key in ("cover", "chat_icon", "banner"):
        if not isinstance(extras.get(key), str):
            raise ValueError(f"缺少 extras.{key} 路径")
    for key, value in extras.items():
        if key not in ("cover", "chat_icon", "banner", "appreciation_guide", "appreciation_thanks"):
            raise ValueError(f"未知 extras 字段：{key}")
        if not isinstance(value, str):
            raise ValueError(f"extras.{key} 须为文件路径字符串")
        paths.append((f"extras.{key}", base / value))
    for label, path in paths:
        if not path.is_file():
            raise ValueError(f"缺少文件 {label}: {path}")
    return paths


def previews(root, items, title, font_path, profile_date):
    directory = root / "previews"
    directory.mkdir()
    for name, color, ink in (("light", (248, 247, 244), (65, 55, 46)), ("dark", (37, 39, 43), (241, 237, 229))):
        sheet = Image.new("RGB", (1280, 170 + ((len(items)+3)//4)*300), color)
        draw = ImageDraw.Draw(sheet)
        draw.text((40, 24), title, font=ImageFont.truetype(font_path, 44), fill=ink)
        draw.text((40, 82), f"{len(items)}张静态表情 · 猫猫与文字白描边", font=ImageFont.truetype(font_path, 24), fill=ink)
        for i, item in enumerate(items):
            im = resize_alpha(Image.open(root / item["master"]).convert("RGBA"), (282, 282))
            x, y = 24 + (i % 4) * 314, 140 + (i // 4) * 300
            sheet.paste(im, (x, y), im)
            draw.text((x+2, y+2), item["number"], font=ImageFont.truetype(font_path, 16), fill=ink)
        sheet.save(directory / f"overview_{name}.jpg", quality=92, optimize=True)
    cards = "\n".join(
        f'<article><div class="image"><img width="240" height="240" src="{x["main_png"]}" alt="{html.escape(x["caption"], quote=True)}"></div><p>{x["number"]} · {html.escape(x["caption"])}</p><small>{html.escape(" / ".join(x["characters"]))}</small></article>' for x in items)
    extras = "\n".join(f'<figure><img src="extras/{p.name}" alt="{p.name}"><figcaption>{p.name}</figcaption></figure>' for p in sorted((root/"extras").glob("*")))
    document = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>*{box-sizing:border-box}body{margin:0;background:#25272b;color:#f4f0e9;font:16px system-ui,sans-serif}header,main,footer{max-width:1320px;margin:auto;padding:24px}button,a{font:inherit}button{cursor:pointer;padding:8px 14px;border:1px solid #888;border-radius:8px;background:transparent;color:inherit;margin:4px}a{color:#deb988;margin-right:20px}h1{margin:0 0 12px}p{line-height:1.6}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(252px,1fr));gap:16px}article{border:1px solid #8885;border-radius:14px;text-align:center;padding:8px}.image{height:240px;display:flex;justify-content:center}.image img{object-fit:contain}article p{margin:6px 0 0}small{opacity:.7}.light{background:#f5f5f5;color:#282625}.light a{color:#825629}.checker .image{background:conic-gradient(#dedede 25%,#fafafa 0 50%,#dedede 0 75%,#fafafa 0) 0 0/20px 20px}.extras{display:flex;gap:16px;flex-wrap:wrap}.extras img{max-width:100%;max-height:230px;object-fit:contain}.extras figure{margin:0;max-width:750px}figcaption{font-size:12px;opacity:.7}footer{border-top:1px solid #8885}</style>
<header><h1>__TITLE__</h1><p>__COUNT__ 张静态表情 · 实际 240px 显示 · 猫猫和文字均有白色描边</p><button onclick="document.body.className=''">深色背景</button><button onclick="document.body.className='light'">浅色背景</button><button onclick="document.body.className='light checker'">透明棋盘</button><p>背景仅供预览，PNG 文件保留真实透明通道。GIF 是单帧兼容格式。技术检查、视觉复核与平台审核分别记录。</p></header>
<main><section class="grid">__CARDS__</section><h2>配套素材</h2><section class="extras">__EXTRAS__</section></main>
<footer><a href="submission_PNG.zip">PNG 投稿素材</a><a href="submission_GIF.zip">单帧 GIF 投稿素材</a><a href="complete_delivery.zip">完整制作文件</a><a href="validation_report.json">技术检查</a><a href="visual_review.json">视觉复核</a><p>已于__PROFILE_DATE__复核官方公开帮助文档的制作规范，采用更小体积目标。封面和50px聊天图标无白色描边。未登录投稿或取得平台审核通过。</p></footer></html>'''
    (root / "preview.html").write_text(document.replace("__COUNT__", str(len(items))).replace("__PROFILE_DATE__", profile_date).replace("__TITLE__", html.escape(title)).replace("__CARDS__", cards).replace("__EXTRAS__", extras), encoding="utf-8")


def build(job_path, output, font_override=None, package=True):
    job = json.loads(job_path.read_text(encoding="utf-8"))
    validate_job(job, job_path.parent)
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    if profile.get("count") != len(job["items"]):
        raise ValueError("平台快照count必须与本版实际items一致")
    style = job.get("style", {})
    radius = style.get("outline_radius", 12)
    if not isinstance(radius, int) or not 6 <= radius <= 16:
        raise ValueError("style.outline_radius 须为1024母版上的6至16整数像素，默认12")
    typography = [caption_typography(style, item, i) for i, item in enumerate(job["items"])]
    if style.get('caption_position','top') != 'top':
        raise ValueError('当前模板采用头顶文字排版，caption_position 必须为 top')
    font_value = font_override or style.get("font")
    if font_value and not Path(font_value).expanduser().is_absolute():
        font_value = str(job_path.parent / font_value)
    font_path = find_font(font_value)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"输出目录非空，请选择新版本目录以保留已有结果：{output}")
    # Preflight every alpha source before writing or creating any package.
    for item in job["items"]:
        read_alpha(job_path.parent / item["art"])
    for name in ("cover", "chat_icon"):
        read_alpha(job_path.parent / job["extras"][name])
    output.mkdir(parents=True, exist_ok=True)
    (output / ".build_incomplete").write_text("未完成打包校验，不应作为最终交付。\n", encoding="utf-8")
    dump(output / "platform-profile.json", profile)
    (output / "scripts").mkdir()
    for script_name in ("build_pack.py", "validate_pack.py", "pack_utils.py"):
        shutil.copyfile(Path(__file__).resolve().parent / script_name, output / "scripts" / script_name)
    archived_job = copy.deepcopy(job)
    manifest = []
    sources = []
    for i, item in enumerate(job["items"], 1):
        number = f"{i:02d}"
        src = (job_path.parent / item["art"]).resolve()
        art = read_alpha(src)
        source_path = output / "sources" / f"{number}.png"
        save_png(art, source_path)
        archived_job["items"][i-1]["art"] = f"sources/{number}.png"
        sources.append({"number": number, "source": str(src), "source_sha256": sha(src), "native_size": list(art.size)})
        art_layer = fit_art(art, (1024, 1024), (34, 238, 490, 754) if item.get("pie_chart") else (34, 238, 956, 754))
        if item.get("pie_chart"):
            # Native diagram: exactly 30% = 108 degrees, separate from generated cat art.
            diagram = Image.new("RGBA", (1024, 1024))
            d = ImageDraw.Draw(diagram)
            box = (606, 432, 946, 772)
            d.ellipse(box, fill="#E8DAD0", outline="#433535", width=8)
            d.pieslice(box, start=-90, end=18, fill="#81A9DC", outline="#433535", width=8)
            d.ellipse(box, outline="#433535", width=8)
            percent_font = ImageFont.truetype(font_path, 66)
            d.text((776, 832), "30%", font=percent_font, fill="#433535", anchor="mm")
            save_png(diagram, output / "layers" / f"{number}_diagram.png")
            art_layer.alpha_composite(diagram)
        letter = typography[i-1]
        text_radius = letter["white_radius"]
        letter_args = {"white_radius": text_radius, "stroke_color": letter["stroke"],
                       "stroke_radius": letter["stroke_radius"], "fill_expand": letter["fill_expand"]}
        words, font_size = text_layer(item["caption"], font_path, letter["fill"], **letter_args)
        outlined_words, _ = text_layer(item["caption"], font_path, letter["fill"], outlined=True, **letter_args)
        archived_job["items"][i-1]["text_color"] = letter["fill"]
        save_png(art_layer, output / "layers" / f"{number}_art.png")
        save_png(words, output / "layers" / f"{number}_text.png")
        master = outline(art_layer, radius, smooth_art=True)
        master.alpha_composite(outlined_words)
        save_png(master, output / "masters" / f"{number}.png")
        main = resize_alpha(master, (240, 240))
        save_png(main, output / "main_png" / f"{number}.png", profile["main_png"]["limit"])
        save_png(resize_alpha(master, (120, 120)), output / "thumbnail" / f"{number}.png", profile["thumbnail"]["limit"])
        save_gif(main, output / "main_gif" / f"{number}.gif", profile["main_gif"]["limit"])
        manifest.append({"number": number, "caption": item["caption"], "meaning": item["meaning"],
                         "characters": item["characters"], "source": f"sources/{number}.png",
                         "main_png": f"main_png/{number}.png", "main_gif": f"main_gif/{number}.gif",
                         "thumbnail": f"thumbnail/{number}.png", "master": f"masters/{number}.png",
                         "art_layer": f"layers/{number}_art.png", "text_layer": f"layers/{number}_text.png",
                         "font_size_master": font_size, "outline_radius_master": radius,
                         "outline_radius_main": radius*240/1024, "outline_color": "#FFFFFF",
                         "caption_position":"top","text_outline_radius_master":text_radius,
                         "typography": letter})
    for key, value in job["extras"].items():
        src = (job_path.parent / value).resolve()
        archived_source = output / "sources" / f"{key}{src.suffix.lower()}"
        shutil.copyfile(src, archived_source)
        archived_job["extras"][key] = archived_source.relative_to(output).as_posix()
        sources.append({"extra": key, "source": str(src), "source_sha256": sha(src)})
        if key in ("cover", "chat_icon"):
            art = fit_art(read_alpha(src), (1024, 1024), (48, 48, 928, 928))
            # The current official guide forbids white contours on covers/icons.
            master = art
            save_png(master, output / "masters" / f"{key}.png")
            targets = [key, "chat_icon_compat"] if key == "chat_icon" else [key]
            for target in targets:
                spec = profile["extras"][target]
                save_png(resize_alpha(master, spec["size"]), output / "extras" / spec["file"], spec["limit"])
        else:
            spec = profile["extras"][key]
            save_opaque(src, output / "extras" / spec["file"], spec)
    dump(output / "job.json", archived_job)
    dump(output / "manifest.json", manifest)
    dump(output / "provenance.json", {"sources": sources, "font": font_path, "font_sha256": sha(Path(font_path)),
                                       "font_index": font_index(font_path), "typography": typography,
                                       "gif": "single-frame static"})
    # A new render invalidates prior visual approvals, even when job metadata was reused.
    dump(output / "visual_review.json", {"status": "pending", "reviewer": "", "items": [], "extras": {},
                                        "issues": [], "background_modes": [], "actual_size_px": []})
    with (output / "captions.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["number", "caption", "meaning", "characters", "main_png", "main_gif", "thumbnail"])
        for x in manifest:
            writer.writerow([x["number"], x["caption"], x["meaning"], "/".join(x["characters"]), x["main_png"], x["main_gif"], x["thumbnail"]])
    previews(output, manifest, job["title"], font_path, profile["basis_date"])
    (output / "delivery_notes.md").write_text(
        f'# {job["title"]}\n\n{len(job["items"])}张静态表情；PNG与单帧GIF分别打包。猫、道具、文字均有白描边，底图真实透明。\n\n'
        'main_png 为240px主图；extras 包含无白边封面、50px聊天图标和750×400有色无字横幅。thumbnail 的120px缩略图和240px图标是兼容备用。赞赏功能未选择，不需要其可选素材。\n\n'
        f'已于{profile["basis_date"]}复核独立官方公开帮助文档的制作规范，导出体积采用更小目标。尚未登录投稿或取得平台审核通过。技术检查见 validation_report.json；角色身份、动作、猫脚/尾巴、中文与白边等实际视觉复核见 visual_review.json。\n\n'
        'sources 保存真实原画，layers 保存未加白色外沿的图层（彩色文字含深色描边），masters 保存1024px成品。逐张字色与描边参数记录在 manifest.json 的 typography；job.json 的素材路径可随交付目录迁移，字体记录在 provenance.json，字体不随包复制。\n', encoding="utf-8")
    from validate_pack import validate, make_packages
    report = validate(output)
    if not report["technical_pass"]:
        raise ValueError("技术检查未通过，未创建投稿包；见 validation_report.json")
    if package:
        make_packages(output)
    (output / ".build_incomplete").unlink()
    return {"output": str(output), "count": len(job["items"]), "technical_checks": len(report["checks"]),
            "visual_review": report["visual_review"], "packages": package, "platform_approval": "not_submitted"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--font")
    parser.add_argument("--no-package", action="store_true", help="先输出素材用于视觉复核，随后 validate_pack.py --package")
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.job.resolve(), args.out.resolve(), args.font, not args.no_package), ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"BUILD FAILED: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
