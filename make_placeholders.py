from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

IMAGES_DIR = Path("images")

MISSING = {
    "15": "Северная Осетия",
    "20": "Чеченская Республика",
    "21": "Чувашия",
    "36": "Воронежская область",
    "39": "Калининградская область",
    "47": "Ленинградская область",
    "66": "Свердловская область",
    "70": "Томская область",
    "72": "Тюменская область",
    "76": "Ярославская область",
    "77": "Москва",
    "78": "Санкт-Петербург",
    "82": "Республика Крым",
    "86": "ХМАО — Югра",
}

for code, name in MISSING.items():
    img = Image.new("RGB", (600, 400), color=(30, 30, 40))
    draw = ImageDraw.Draw(img)
    
    # Код крупно
    try:
        font_big = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
    except:
        font_big = ImageFont.load_default()
    
    try:
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except:
        font_small = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), code, font=font_big)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(((600 - text_w) / 2, (400 - text_h) / 2 - 20), code, fill=(255, 255, 255), font=font_big)
    
    bbox2 = draw.textbbox((0, 0), name, font=font_small)
    name_w = bbox2[2] - bbox2[0]
    draw.text(((600 - name_w) / 2, 400 / 2 + 30), name, fill=(200, 200, 200), font=font_small)
    
    path = IMAGES_DIR / f"{code}.jpg"
    img.save(path)
    print(f"✅ Создана заглушка: {code}.jpg — {name}")

print("\nГотово!")
