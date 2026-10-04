#!/usr/bin/env python3
"""Validate exported local assets; --package creates archives only after success."""
from pathlib import Path
import argparse
import csv
import io
import json
import re
import sys
import zipfile

import numpy as np
from PIL import Image, ImageColor

from pack_utils import caption_typography, dump, sha, read_alpha, fit_art, resize_alpha


def assess_visual_review(review, job):
    """Check review evidence consistency; this does not perform image inspection."""
    fields = ("identity", "anatomy", "caption", "outline", "pose", "readability")
    reviewed = review.get("items", [])
    issues = review.get("issues")
    modes = review.get("background_modes")
    sizes = review.get("actual_size_px")
    return bool(review.get("status") == "passed" and bool(review.get("reviewer"))
                and isinstance(issues, list) and not issues
                and isinstance(modes, list) and all(mode in modes for mode in ("dark", "light", "checker"))
                and isinstance(sizes, list) and 240 in sizes
                and [x.get("number") for x in reviewed] == [f"{i:02d}" for i in range(1, len(job["items"])+1)]
                and all(all(x.get(k) is True for k in fields) for x in reviewed)
                and all(review.get("extras", {}).get(k) is True for k in job["extras"]))


def validate(root):
    checks, inventory = [], []

    def check(ok, label, detail=""):
        checks.append({"pass": bool(ok), "check": label, "detail": str(detail)})

    def inspect(path, spec, padding=2):
        name = path.relative_to(root).as_posix()
        if not path.is_file():
            check(False, name, "missing")
            return None
        try:
            with Image.open(path) as im:
                im.load()
                check(list(im.size) == spec["size"], name + " dimensions", im.size)
                check(im.format == spec["format"], name + " format", im.format)
                check(path.stat().st_size <= spec["limit"], name + " bytes", path.stat().st_size)
                check(getattr(im, "n_frames", 1) == 1, name + " static single frame")
                rgba = np.array(im.convert("RGBA"))
                a = rgba[..., 3]
                if spec["alpha"]:
                    check(a.min() == 0 and a.max() == 255, name + " genuine alpha")
                    check(not any(a[y, x] for x, y in ((0, 0), (im.width-1, 0), (0, im.height-1), (im.width-1, im.height-1))), name + " transparent corners")
                    ys, xs = np.nonzero(a >= 8)
                    if len(xs):
                        pad = min(xs.min(), ys.min(), im.width-1-xs.max(), im.height-1-ys.max())
                        check(pad >= padding, name + " safe margin", pad)
                        check(.015 < float((a >= 8).mean()) < .9, name + " nonempty cutout")
                    else:
                        check(False, name + " nonempty cutout")
                else:
                    check(np.all(a == 255), name + " opaque designed background")
                inventory.append({"file": name, "size": list(im.size), "bytes": path.stat().st_size,
                                  "format": im.format, "sha256": sha(path)})
                return rgba
        except (OSError, ValueError) as error:
            check(False, name, error)
            return None

    profile = json.loads((root / "platform-profile.json").read_text(encoding="utf-8"))
    items = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    job = json.loads((root / "job.json").read_text(encoding="utf-8"))
    check(isinstance(job.get('characters'),list) and len(job['characters'])==1, 'exactly one cat')
    check(8 <= len(items) <= 24 and len(items) == profile.get("count") == job.get("count"), "actual 8-24 count matches job and profile")
    check([x["number"] for x in items] == [f"{i:02d}" for i in range(1, len(job["items"])+1)], "continuous numbering matches actual count")
    check([x["caption"] for x in items] == [x["caption"] for x in job["items"]], "verbatim ordered captions")
    check([x["characters"] for x in items] == [x["characters"] for x in job["items"]], "cast matches plan")
    meanings = [x["meaning"] for x in items]
    check(len(set(meanings)) == len(items) and all(1 <= len(x) <= 4 for x in meanings), "unique 1-4 character meanings")
    for folder, extension in (("main_png", "png"), ("main_gif", "gif"), ("thumbnail", "png")):
        files = {x.name for x in (root / folder).iterdir() if x.is_file()} if (root / folder).exists() else set()
        check(files == {f"{i:02d}.{extension}" for i in range(1, len(job["items"])+1)}, folder + " exact files", len(files))
    for index, item in enumerate(items):
        number = item["number"]
        paths_safe = True
        for key in ("source", "main_png", "main_gif", "thumbnail", "master", "art_layer", "text_layer"):
            path = (root / item[key]).resolve()
            try:
                path.relative_to(root.resolve())
            except ValueError:
                paths_safe = False
            check(path.is_file() and paths_safe, f"{number} manifest path {key}")
        if not paths_safe:
            continue
        main = inspect(root / item["main_png"], profile["main_png"])
        gif = inspect(root / item["main_gif"], profile["main_gif"])
        thumb = inspect(root / item["thumbnail"], profile["thumbnail"])
        if main is not None and gif is not None and main.shape == gif.shape:
            a, b = main[..., 3] >= 96, gif[..., 3] > 0
            iou = float((a & b).sum()) / max(1, int((a | b).sum()))
            check(iou >= .985, number + " PNG/GIF shape match", round(iou, 6))
        if main is not None and thumb is not None and thumb.shape[:2] == (120, 120):
            a = np.array(Image.fromarray(main[..., 3]).resize((120, 120), Image.Resampling.LANCZOS)) >= 96
            b = thumb[..., 3] >= 96
            iou = float((a & b).sum()) / max(1, int((a | b).sum()))
            check(iou >= .97, number + " main/thumbnail shape match", round(iou, 6))
        try:
            with Image.open(root / item["source"]) as im:
                check(im.mode == "RGBA" and min(im.size) >= 1024, number + " native RGBA source", im.size)
            art = Image.open(root / item["art_layer"]).convert("RGBA")
            words = Image.open(root / item["text_layer"]).convert("RGBA")
            letter = caption_typography(job.get("style", {}), job["items"][index], index)
            if "typography" in item or letter["mode"] == "colorful":
                check(item.get("typography") == letter, number + " typography matches plan")
            if letter["mode"] == "colorful":
                pixels = np.array(words)
                for label in ("fill", "stroke"):
                    rgb = np.array(ImageColor.getrgb(letter[label]))
                    count = int(((pixels[..., :3] == rgb).all(axis=2) & (pixels[..., 3] == 255)).sum())
                    check(count > 200, f"{number} text {label} exact color", f'{letter[label]} pixels={count}')
                    if main is not None:
                        # Check the real 240px caption, allowing antialiasing/PNG quantization.
                        caption = main[:57].astype(np.int16)
                        count_small = int(((np.abs(caption[..., :3] - rgb) <= 20).all(axis=2)
                                           & (caption[..., 3] >= 230)).sum())
                        check(count_small > 20, f"{number} text {label} visible at 240px", count_small)
            base = np.array(Image.alpha_composite(art, words))
            with Image.open(root / item["master"]) as im:
                check(im.size == (1024, 1024) and im.mode == "RGBA", number + " master 1024 RGBA")
                after = np.array(im.convert("RGBA"))
            if after.shape != base.shape:
                check(False, number + " master/layer dimensions agree")
                continue
            core = base[..., 3] == 255
            check(np.array_equal(base[core], after[core]), number + " opaque art and text preserved")
            check(np.all(after[..., 3] >= base[..., 3]), number + " no alpha lost")
            added = (base[..., 3] == 0) & (after[..., 3] >= 250) & (after[..., :3].min(axis=2) >= 250)
            for label, layer in (("art", art), ("text", words)):
                bounds = layer.getbbox()
                if bounds:
                    r = item["outline_radius_master"] + 2
                    left, top, right, bottom = bounds
                    count = int(added[max(0, top-r):min(1024, bottom+r), max(0, left-r):min(1024, right+r)].sum())
                    check(count > 500, f"{number} {label} white outline", count)
                else:
                    check(False, f"{number} {label} nonempty")
        except (OSError, ValueError) as error:
            check(False, number + " original/master proof", error)
    for key, spec in profile["extras"].items():
        if spec.get("optional") and key not in job["extras"]:
            continue
        inspect(root / "extras" / spec["file"], spec, 1 if key == "chat_icon_compat" else 2)
    for key in ("cover", "chat_icon"):
        if profile["extras"][key].get("outline") is False:
            expected = fit_art(read_alpha(root / job["extras"][key]), (1024, 1024), (48, 48, 928, 928))
            actual = Image.open(root / "masters" / f"{key}.png").convert("RGBA")
            check(np.array_equal(np.array(expected), np.array(actual)), key + " no added white contour")
            targets = [key, 'chat_icon_compat'] if key == 'chat_icon' else [key]
            for target in targets:
                spec = profile['extras'][target]
                rendered = Image.open(root / 'extras' / spec['file']).convert('RGBA')
                check(np.array_equal(np.array(rendered.getchannel('A')),
                                     np.array(resize_alpha(actual, spec['size']).getchannel('A'))),
                      target + ' alpha preserved through PNG compression')
    main_hashes = [x["sha256"] for x in inventory if x["file"].startswith("main_png/")]
    check(len(main_hashes) == len(set(main_hashes)) == len(items), "all main files distinct")
    if (root / "preview.html").exists():
        markup = (root / "preview.html").read_text(encoding="utf-8")
        for link in re.findall(r'(?:src|href)="([^"]+)"', markup):
            if link.endswith(".zip") or link == "validation_report.json":
                continue  # Report/archives are created after these checks.
            check((root / link).is_file(), "preview local link", link)
    else:
        check(False, "preview.html exists")
    review = json.loads((root / "visual_review.json").read_text(encoding="utf-8"))
    visual_assets_match = review.get('asset_sha256') == {x['file']:x['sha256'] for x in inventory}
    visual_complete = assess_visual_review(review, job) and visual_assets_match
    # Never upgrade a missing visual inspection to passed based on pixel tests.
    source_hashes = [sha(root / x["source"]) for x in items if (root / x["source"]).is_file()]
    warnings = []
    if len(set(source_hashes)) < len(source_hashes):
        warnings.append("存在重复原画；须确认是用户要求复用，而非用同一姿势代替不同情绪。")
    report = {"technical_pass": all(x["pass"] for x in checks), "checks": checks, "assets": inventory, "warnings": warnings,
              "visual_review": "passed" if visual_complete else "pending_or_failed",
              "visual_complete": bool(visual_complete), "visual_asset_hashes_match":visual_assets_match,
              "official_rules_verified": profile["official_rules_verified"],
              "platform_approval": "not_submitted", "profile": profile["name"]}
    dump(root / "validation_report.json", report)
    return report


def make_packages(root):
    report = json.loads((root / "validation_report.json").read_text(encoding="utf-8"))
    if not report["technical_pass"]:
        raise ValueError("技术检查失败，禁止打包")
    if not report.get('visual_complete'):
        raise ValueError('尚未完成全部主图和配套素材的视觉复核，禁止生成最终投稿包')
    items = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    job = json.loads((root / "job.json").read_text(encoding="utf-8"))
    archives = []
    for encoding in ("PNG", "GIF"):
        path = root / f"submission_{encoding}.zip"
        entries = [{"number": x["number"], "caption": x["caption"], "meaning": x["meaning"], "characters": x["characters"],
                    "main": f'main/{x["number"]}.{encoding.lower()}', "thumbnail": x["thumbnail"]} for x in items]
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for p in sorted((root / f"main_{encoding.lower()}").iterdir()):
                archive.write(p, "main/" + p.name)
            for folder in ("thumbnail", "extras"):
                for p in sorted((root / folder).iterdir()):
                    archive.write(p, p.relative_to(root).as_posix())
            for filename in ("platform-profile.json", "validation_report.json", "visual_review.json", "delivery_notes.md", "上传填写文案.md"):
                archive.write(root / filename, filename)
            archive.writestr("manifest.json", json.dumps(entries, ensure_ascii=False, indent=2) + "\n")
            stream = io.StringIO()
            writer = csv.writer(stream)
            writer.writerow(["number", "caption", "meaning", "characters", "main", "thumbnail"])
            for x in entries:
                writer.writerow([x["number"], x["caption"], x["meaning"], "/".join(x["characters"]), x["main"], x["thumbnail"]])
            archive.writestr("captions.csv", stream.getvalue().encode("utf-8-sig"))
        archives.append(path)
    path = root / "complete_delivery.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.suffix == ".zip" or "__pycache__" in p.parts or p.name in (".build_incomplete", "zip_validation.json", "SHA256SUMS.txt", ".DS_Store"):
                continue
            name = p.relative_to(root).as_posix()
            if name == "preview.html":
                # The self-contained backup deliberately excludes ZIPs, so its
                # preview must not point at archives that only exist outside it.
                markup = p.read_text(encoding="utf-8")
                markup = re.sub(r'<a\s+href="[^"]+\.zip"[^>]*>.*?</a>', "", markup, flags=re.DOTALL)
                archive.writestr(name, markup)
            else:
                archive.write(p, name)
    archives.append(path)
    results = []
    for path in archives:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if archive.testzip() is not None or len(names) != len(set(names)) or any(n.startswith("/") or ".." in Path(n).parts for n in names):
                raise ValueError(f"ZIP完整性或路径失败：{path.name}")
            if path.name.startswith("submission_"):
                scoped = json.loads(archive.read("manifest.json"))
                if len(scoped) != len(items) or any(x["main"] not in names or x["thumbnail"] not in names for x in scoped):
                    raise ValueError(f"ZIP清单引用失效：{path.name}")
                if sum(n.startswith("main/") for n in names) != len(items) or sum(n.startswith("thumbnail/") for n in names) != len(items):
                    raise ValueError(f"ZIP文件数量错误：{path.name}")
                if any(n.startswith(("sources/", "layers/", "masters/")) for n in names):
                    raise ValueError(f"投稿ZIP混入原画：{path.name}")
            html_links_checked = 0
            for html_file in (name for name in names if name.endswith(".html")):
                markup = archive.read(html_file).decode("utf-8")
                for link in re.findall(r'(?:src|href)="([^"]+)"', markup):
                    if link.startswith(("https://", "http://", "data:", "#")):
                        continue
                    target = (Path(html_file).parent / link.split("#", 1)[0]).as_posix()
                    if target not in names:
                        raise ValueError(f"ZIP内网页引用失效：{path.name}: {html_file} → {link}")
                    html_links_checked += 1
            results.append({"file": path.name, "files": len(names), "bytes": path.stat().st_size, "sha256": sha(path), "testzip": "pass", "html_links_checked": html_links_checked})
    dump(root / "zip_validation.json", results)
    (root / "SHA256SUMS.txt").write_text("".join(f'{x["sha256"]}  {x["file"]}\n' for x in results), encoding="utf-8")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--package", action="store_true")
    args = parser.parse_args()
    root = args.pack.resolve()
    try:
        report = validate(root)
        failed = [x for x in report["checks"] if not x["pass"]]
        print(json.dumps({"technical_pass": report["technical_pass"], "checks": len(report["checks"]),
                          "failed": failed, "visual_review": report["visual_review"]}, ensure_ascii=False))
        if not report["technical_pass"]:
            raise SystemExit(1)
        if args.package:
            print(json.dumps(make_packages(root), ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"VALIDATION FAILED: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
