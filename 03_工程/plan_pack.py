#!/usr/bin/env python3
"""Validate a minimal caption/cat request and create portable production plans."""
import argparse
import json
from pathlib import Path
import re
import shutil
from pack_utils import CAPTION_PALETTE

SKILL_ROOT = Path(__file__).resolve().parent.parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slug(text):
    result = re.sub(r"[^\w\-\u4e00-\u9fff]+", "_", text).strip("_")
    return result[:70] or "stickers"


def make_plans(request, output, registry_path):
    if not isinstance(request, dict):
        raise ValueError("输入必须是 JSON 对象")
    names = request.get("cats", [request["cat"]] if "cat" in request else [])
    if names is None or names == [] or names == "":
        raise ValueError("缺少猫咪姓名。请提供 1 只猫的名字（奶思、古德或范恩）。")
    if not isinstance(names, list) or any(not isinstance(n, str) or not n.strip() for n in names):
        raise ValueError("猫咪姓名格式有误。请只提供 1 个非空猫名。")
    if len(names) != 1:
        raise ValueError(f"本 Skill 每次只接受 1 只猫，你提供了 {len(names)} 个猫名：{'、'.join(names)}。请保留一个。")
    names = [names[0].strip()]
    if "cat" in request and "cats" in request and request["cat"] != names[0]:
        raise ValueError("cat 与 cats 指定的猫名不一致。请只保留 1 个猫名字段。")
    mode = request.get("mode", "single")
    if mode != "single":
        raise ValueError("本 Skill 只支持 single 单猫一套，不支持混合猫咪或多套扩展。")
    captions = request.get("captions")
    if not isinstance(captions, list) or len(captions) != 24:
        raise ValueError("captions 必须恰好有 24 条；请保留用户原文，不自动补齐")
    if any(not isinstance(c, str) or not c.strip() for c in captions):
        raise ValueError("每条文案必须是非空字符串")
    registry_path = Path(registry_path).resolve()
    registry = read_json(registry_path)
    skill_root = registry_path.parent.parent
    index = {}
    for cat in registry["characters"]:
        for alias in [cat["name"], *cat.get("aliases", [])]:
            if alias in index and index[alias]["id"] != cat["id"]:
                raise ValueError(f"角色库别名冲突：{alias}")
            index[alias] = cat
    if names[0] not in index:
        combined = [p for p in re.split(r"[、,，/;；\s]+|和|与|及", names[0]) if p]
        if len(combined)>1:
            raise ValueError(f"本 Skill 每次只接受 1 只猫，你提供了 {len(combined)} 个猫名：{'、'.join(combined)}。请保留一个。")
    unknown = [n for n in names if n not in index]
    if unknown:
        raise ValueError("缺少角色参考，请补充姓名映射或形象依据：" + "、".join(unknown))
    cats = [index[n] for n in names]
    if len({c["id"] for c in cats}) != len(cats):
        raise ValueError("同一角色被重复输入，请核对姓名与别名")
    refs = {}
    for cat in cats:
        refs[cat["id"]] = []
        if not cat.get("references"):
            raise ValueError(f"角色 {cat['name']} 缺少参考")
        for ref in cat["references"]:
            path = (skill_root / ref["path"]).resolve()
            if not path.is_file():
                raise ValueError(f"角色参考文件不存在：{path}")
            refs[cat["id"]].append((ref, path))
    output = Path(output).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError(f"输出目录非空，避免覆盖已有制作：{output}")
    # Validate the entire input before creating any output.
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "input.json", request)
    groups = [cats]
    batch = {"mode": mode, "pack_count": len(groups), "sticker_count": 24 * len(groups), "plans": []}
    for number, group in enumerate(groups, 1):
        group_names = [c["name"] for c in group]
        title_base = request.get("title") or "日常小表情"
        title = "、".join(group_names) + "_" + str(title_base)
        pack_dir = output / f"{number:02d}_{slug(title)}"
        (pack_dir / "references").mkdir(parents=True)
        local_characters = []
        for cat in group:
            local = dict(cat)
            local["references"] = []
            for i, (ref, source) in enumerate(refs[cat["id"]], 1):
                dest = pack_dir / "references" / f"{cat['id']}_{i:02d}{source.suffix}"
                shutil.copy2(source, dest)
                local["references"].append({**ref, "path": str(dest.relative_to(pack_dir)), "bundled_source": str(source)})
            local_characters.append(local)
        write_json(pack_dir / "character_references.json", local_characters)
        items = []
        for i, caption in enumerate(captions):
            items.append({"number": f"{i+1:02d}", "caption": caption, "meaning": "", "characters": [group_names[i % len(group_names)]], "scene": {"emotion": "", "pose": "", "props": [], "interaction": "", "tail": "", "composition": ""}, "art": ""})
        job = {"title": title, "characters": group_names, "status": "planning", "items": items, "extras": {"cover": "", "chat_icon": "", "banner": ""}, "style": {"text_style": "colorful", "text_palette": list(CAPTION_PALETTE), "text_stroke_color": "#433535", "text_stroke_radius": 6, "text_fill_expand": 2, "outline_radius": 12, "text_outline_radius": 10, "caption_position": "top"}, "review": {"status": "pending", "reviewer": "", "items": [], "extras": {}, "issues": [], "background_modes": [], "actual_size_px": []}}
        write_json(pack_dir / "job-plan.json", job)
        batch["plans"].append(str((pack_dir / "job-plan.json").relative_to(output)))
    write_json(output / "batch.json", batch)
    return batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--registry", type=Path, default=SKILL_ROOT / "references" / "characters.json")
    args = parser.parse_args()
    try:
        result = make_plans(read_json(args.input), args.out, args.registry)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(2, f"无法建立计划：{exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
