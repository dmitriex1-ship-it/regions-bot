from PIL import Image, ImageFilter, ImageDraw, ImageFont
from pathlib import Path

IMAGES_DIR = Path("images")
BLUR_DIR = Path("images_blur")
BLUR_DIR.mkdir(exist_ok=True)

for img_path in sorted(IMAGES_DIR.glob("*.jpg")):
    try:
        img = Image.open(img_path)
        img.verify()  # проверяем, не битый ли файл
        img = Image.open(img_path)  # открываем заново после verify
        
        blurred = img.filter(ImageFilter.GaussianBlur(radius=20))
        
        draw = ImageDraw.Draw(blurred)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except:
            font = ImageFont.load_default()
        
        text = "👆 Нажми, чтобы увидеть"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text(((600 - text_w) / 2, 400 / 2), text, fill=(255, 255, 255), font=font)
        
        out_path = BLUR_DIR / img_path.name
        blurred.save(out_path)
        print(f"✅ Размыто: {img_path.name}")
    except Exception as e:
        print(f"❌ Пропущен {img_path.name}: {e}")

print("\nГотово!")
