"""One-off script to generate the static OG share image.
Run: python scripts/generate_og_image.py
Output: web/public/og.png (1200x630)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (10, 11, 13)
ACCENT = (36, 81, 214)
TEXT = (228, 228, 231)
MUTED = (113, 113, 122)

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)


def load_font(size, bold=False):
    names = (
        ["arialbd.ttf", "DejaVuSans-Bold.ttf"]
        if bold
        else ["arial.ttf", "DejaVuSans.ttf"]
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


title_font = load_font(64, bold=True)
sub_font = load_font(28)
brand_font = load_font(28, bold=True)
tag_font = load_font(22)

# brand mark
draw.rounded_rectangle([(80, 70), (124, 114)], radius=10, fill=ACCENT)
draw.text((140, 78), "Cap Rate Lens", font=brand_font, fill=TEXT)

# headline
lines = ["How cap rate moves reshape", "ASX property trust valuations"]
y = 220
for line in lines:
    draw.text((80, y), line, font=title_font, fill=TEXT)
    y += 78

# subtext
draw.text(
    (80, 400),
    "Live cap rate sensitivity modelling across 8 ASX-listed property trusts",
    font=sub_font,
    fill=MUTED,
)

# footer tag
draw.text((80, 540), "cap-rate-lens", font=tag_font, fill=ACCENT)

out_dir = Path(__file__).parent.parent / "web" / "public"
out_dir.mkdir(exist_ok=True)
img.save(out_dir / "og.png")
print(f"Saved to {out_dir / 'og.png'}")
