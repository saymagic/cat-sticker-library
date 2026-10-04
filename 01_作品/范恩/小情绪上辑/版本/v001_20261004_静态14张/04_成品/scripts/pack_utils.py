"""Deterministic image-format helpers. Requires Pillow and numpy; no network."""
from pathlib import Path
import glob
import hashlib
import json
import math
import os

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps, ImageFilter

LANCZOS = Image.Resampling.LANCZOS
CAPTION_PALETTE = ("#EA92AD", "#F2C454", "#81A9DC", "#A6C867",
                   "#AE98D4", "#75BCB7", "#EEA160", "#E58070")
PROFILE = Path(__file__).resolve().parents[1] / "references/platform-profile.json"
if not PROFILE.exists():
    PROFILE = Path(__file__).resolve().parents[1] / "platform-profile.json"
if not PROFILE.exists():
    PROFILE = Path(__file__).resolve().parent / "platform-profile.json"


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def resize_alpha(im, size):
    return im.convert("RGBa").resize(size, LANCZOS).convert("RGBA")


def find_font(explicit=None):
    if explicit:
        candidates = [str(Path(explicit).expanduser())]
    else:
        candidates = []
        if os.environ.get("WECHAT_STICKER_FONT"):
            candidates.append(os.environ["WECHAT_STICKER_FONT"])
        for pattern in (
            "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/*/AssetData/Hannotate.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/*/AssetData/PingFang.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "C:/Windows/Fonts/msyh.ttc",
        ):
            candidates.extend(sorted(glob.glob(pattern)))
    for candidate in candidates:
        try:
            f = ImageFont.truetype(candidate, 40, index=0)
            # Reject obvious Latin-only/tofu fonts. A supplied font still needs visual QA.
            if bytes(f.getmask("猫")) != bytes(f.getmask("优")):
                return candidate
        except OSError:
            continue
    raise ValueError("找不到可用中文字体。请提供 --font 路径或 WECHAT_STICKER_FONT。")


def font_index(font_path):
    return 2 if Path(font_path).name.lower() == 'hannotate.ttc' else 0


def caption_typography(style, item, index):
    """Resolve reproducible per-sticker colors; explicit old ink jobs stay legacy."""
    mode = style.get("text_style", "legacy_coffee" if "ink" in style else "colorful")
    if mode not in ("colorful", "legacy_coffee"):
        raise ValueError("style.text_style 只能为 colorful 或 legacy_coffee")

    def color(value):
        try:
            rgba = ImageColor.getcolor(value, "RGBA")
        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError(f"无效文字颜色：{value!r}") from error
        if rgba[3] != 255:
            raise ValueError("文字颜色须不透明")
        return "#" + "".join(f"{c:02X}" for c in rgba[:3])

    if mode == "colorful":
        palette = style.get("text_palette", CAPTION_PALETTE)
        if not isinstance(palette, (list, tuple)) or not palette:
            raise ValueError("style.text_palette 须为非空颜色列表")
        palette = [color(c) for c in palette]
        fill = color(item.get("text_color", palette[index % len(palette)]))
        stroke = color(style.get("text_stroke_color", "#433535"))
        fill_expand = style.get("text_fill_expand", 2)
        stroke_radius = style.get("text_stroke_radius", 6)
        if not isinstance(fill_expand, int) or not 0 <= fill_expand <= 5:
            raise ValueError("style.text_fill_expand 须为0至5整数像素")
        if not isinstance(stroke_radius, int) or not 3 <= stroke_radius <= 10:
            raise ValueError("style.text_stroke_radius 须为3至10整数像素")
        if fill == stroke:
            raise ValueError("彩色字填充与深色描边不能同色")
    else:
        fill = color(style.get("ink", "#270D02"))
        stroke, fill_expand, stroke_radius = fill, 5, 0
    white_radius = style.get("text_outline_radius", 10 if mode == "colorful" else 17)
    if not isinstance(white_radius, int) or not 8 <= white_radius <= 24:
        raise ValueError("style.text_outline_radius 须为8至24整数像素")
    return {"mode": mode, "fill": fill, "stroke": stroke, "fill_expand": fill_expand,
            "stroke_radius": stroke_radius, "white_radius": white_radius}


def read_alpha(path, minimum=1024):
    with Image.open(path) as src:
        if getattr(src, "n_frames", 1) != 1:
            raise ValueError(f"静态输入应为单帧：{path}")
        if "A" not in src.getbands() and "transparency" not in src.info:
            raise ValueError(f"原画必须含真实 Alpha，不能使用色底或棋盘截图：{path}")
        im = src.convert("RGBA")
    a = np.asarray(im.getchannel("A"))
    if min(im.size) < minimum:
        raise ValueError(f"原画原生分辨率至少 {minimum}px，禁止先放大概览截图：{path} {im.size}")
    if int(a.min()) != 0 or int(a.max()) != 255:
        raise ValueError(f"原画需要透明背景和实心主体：{path}")
    if any(a[y, x] != 0 for x, y in ((0, 0), (im.width-1, 0), (0, im.height-1), (im.width-1, im.height-1))):
        raise ValueError(f"原画四角须透明：{path}")
    if not .005 < float((a > 8).mean()) < .94:
        raise ValueError(f"原画为空或接近整幅不透明：{path}")
    ys, xs = np.nonzero(a >= 8)
    if min(xs.min(), ys.min(), im.width-1-xs.max(), im.height-1-ys.max()) < 1:
        raise ValueError(f"原画主体触边，须先修复被截断的轮廓：{path}")
    return im


def fit_art(im, canvas_size, box):
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a >= 2)
    if not len(xs):
        raise ValueError("原画为空")
    crop = im.crop((max(0, int(xs.min())-4), max(0, int(ys.min())-4),
                    min(im.width, int(xs.max())+5), min(im.height, int(ys.max())+5)))
    x, y, width, height = box
    scale = min(width/crop.width, height/crop.height)
    if scale > 1.01:
        raise ValueError("有效主体像素不足；请生成更大的独立原画，不要放大补足。")
    fitted = resize_alpha(crop, (max(1, round(crop.width*scale)), max(1, round(crop.height*scale))))
    out = Image.new("RGBA", canvas_size)
    out.alpha_composite(fitted, (round(x+(width-fitted.width)/2), round(y+(height-fitted.height)/2)))
    return out


def dilate_disk(alpha, radius):
    a = np.asarray(alpha, dtype=np.uint8)
    horizontal = [a]
    for dx in range(1, radius+1):
        v = horizontal[-1].copy()
        np.maximum(v[:, dx:], a[:, :-dx], out=v[:, dx:])
        np.maximum(v[:, :-dx], a[:, dx:], out=v[:, :-dx])
        horizontal.append(v)
    result = np.zeros_like(a)
    for dy in range(-radius, radius+1):
        dx = int(math.sqrt(radius*radius-dy*dy))
        v = horizontal[dx]
        if dy < 0:
            np.maximum(result[:dy], v[-dy:], out=result[:dy])
        elif dy > 0:
            np.maximum(result[dy:], v[:-dy], out=result[dy:])
        else:
            np.maximum(result, v, out=result)
    return Image.fromarray(result)


def outline(im, radius=12, smooth_art=False):
    white = Image.new("RGBA", im.size, (255, 255, 255, 0))
    alpha = im.getchannel("A")
    if smooth_art:
        alpha = alpha.point(lambda a: 255 if a >= 32 else 0)
        alpha = alpha.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(9))
        alpha = dilate_disk(alpha, radius).filter(ImageFilter.GaussianBlur(1.2))
    else:
        alpha = dilate_disk(alpha, radius)
    white.putalpha(alpha)
    white.alpha_composite(im)
    return white


def text_layer(text, font_path, ink, box=(48, 45, 928, 195), white_radius=17,
               outlined=False, stroke_color=None, stroke_radius=0, fill_expand=5):
    out = Image.new("RGBA", (1024, 1024))
    draw = ImageDraw.Draw(out)
    x, y, width, height = box
    for size in range(196, 111, -2):
        font = ImageFont.truetype(font_path, size, index=font_index(font_path))
        foreground_radius = fill_expand + stroke_radius
        bounds = draw.textbbox((0, 0), text, font=font,
                               stroke_width=foreground_radius+white_radius)
        tw, th = bounds[2]-bounds[0], bounds[3]-bounds[1]
        if tw <= width and th <= height:
            pos=(x+(width-tw)/2-bounds[0], y-bounds[1])
            if outlined:
                draw.text(pos, text, font=font, fill=ink,
                          stroke_width=foreground_radius+white_radius, stroke_fill='white')
            if stroke_radius:
                draw.text(pos, text, font=font, fill=ink,
                          stroke_width=foreground_radius, stroke_fill=stroke_color)
            draw.text(pos, text, font=font, fill=ink, stroke_width=fill_expand, stroke_fill=ink)
            return out, size
    raise ValueError(f"文案过长，240px下难以读清；须先调整排版或由用户确定短文案，不能擅自删字：{text!r}")


def save_png(im, dest, limit=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, format="PNG", optimize=True, compress_level=9)
    if limit and dest.stat().st_size > limit:
        original_alpha = im.getchannel('A') if 'A' in im.getbands() else None
        for colors in (256, 224, 192, 160, 128):
            # Quantize RGB only: RGBA palette averaging can make opaque pixels
            # translucent and change the soft silhouette of a transparent icon.
            reduced = im.convert('RGB').quantize(colors=colors, method=Image.Quantize.FASTOCTREE,
                                                dither=Image.Dither.NONE).convert('RGBA')
            if original_alpha is not None:
                reduced.putalpha(original_alpha)
            reduced.save(dest, format="PNG", optimize=True)
            if dest.stat().st_size <= limit:
                break
    if limit and dest.stat().st_size > limit:
        raise ValueError(f"PNG超过本地体积门槛：{dest.name} {dest.stat().st_size}>{limit}")


def save_gif(im, dest, limit=100000):
    pal = im.convert("RGB").quantize(colors=255, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE)
    pixels = np.array(pal)
    pixels[np.asarray(im.getchannel("A")) < 96] = 255
    out = Image.fromarray(pixels)
    out.putpalette(pal.getpalette()[:765] + [0, 0, 0])
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, format="GIF", transparency=255, disposal=2, optimize=False)
    if dest.stat().st_size > limit:
        raise ValueError(f"GIF超过本地体积门槛：{dest}")


def save_opaque(src, dest, spec):
    with Image.open(src) as raw:
        if raw.width < spec["size"][0] or raw.height < spec["size"][1]:
            raise ValueError(f"配套图原生像素不足：{src} {raw.size}")
        if ("A" in raw.getbands() or "transparency" in raw.info) and raw.convert("RGBA").getchannel("A").getextrema() != (255, 255):
            raise ValueError(f"banner/赞赏图须有完整设计背景，不自动用黑底填透明区：{src}")
        im = ImageOps.fit(raw.convert("RGB"), spec["size"], method=LANCZOS)
    if spec["format"] == "PNG":
        save_png(im, dest, spec["limit"])
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        for quality in range(94, 39, -2):
            im.save(dest, format="JPEG", quality=quality, optimize=True, subsampling=0)
            if dest.stat().st_size <= spec["limit"]:
                return
        raise ValueError(f"JPEG超过本地体积门槛：{dest}")
