"""Dataset Generator for Controlled Synthetic Packages.

Generates photo-realistic controlled synthetic package images and writes corresponding
ground-truth annotations into datasets/real_package_validation/.

CRITICAL RULE (Section 2 & 27):
Every generated artifact is explicitly labeled with dataset_type = "SYNTHETIC_CONTROLLED".
Under no circumstances are these labeled as real-world photographs.
"""

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


def get_default_font(size: int = 20) -> ImageFont.ImageFont:
    """Returns available TrueType font or fallback PIL font."""
    font_paths = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_label_canvas(
    width: int,
    height: int,
    lines: List[Tuple[str, str, int, Tuple[int, int, int]]],
    bg_color: Tuple[int, int, int] = (248, 248, 248),
    border_color: Tuple[int, int, int] = (40, 40, 40),
) -> Image.Image:
    """Renders a package label with border and formatted lines."""
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Draw border
    draw.rectangle([10, 10, width - 10, height - 10], outline=border_color, width=3)

    y_cursor = 25
    for text, style, font_size, color in lines:
        font = get_default_font(font_size)
        if style == "header":
            # Header banner
            bbox = font.getbbox(text)
            text_w = bbox[2] - bbox[0]
            draw.rectangle([20, y_cursor, width - 20, y_cursor + 38], fill=(30, 60, 110))
            draw.text(((width - text_w) // 2, y_cursor + 6), text, font=font, fill=(255, 255, 255))
            y_cursor += 48
        elif style == "rule":
            draw.line([25, y_cursor + 5, width - 25, y_cursor + 5], fill=(180, 180, 180), width=1)
            y_cursor += 15
        elif style == "box":
            draw.rectangle([25, y_cursor, width - 25, y_cursor + 36], outline=(150, 40, 40), width=2, fill=(255, 245, 245))
            draw.text((35, y_cursor + 6), text, font=font, fill=color)
            y_cursor += 44
        else:
            draw.text((25, y_cursor), text, font=font, fill=color)
            bbox = font.getbbox(text)
            text_h = max(bbox[3] - bbox[1], font_size)
            y_cursor += text_h + 8

    return img


def apply_blur(img: Image.Image, radius: float) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def apply_glare_hotspot(img: Image.Image, center_x: int, center_y: int, radius: int = 100, intensity: float = 0.8) -> Image.Image:
    arr = np.array(img).astype(np.float32)
    h, w = arr.shape[:2]
    y_indices, x_indices = np.ogrid[:h, :w]
    dist_sq = (x_indices - center_x) ** 2 + (y_indices - center_y) ** 2
    mask = np.exp(-dist_sq / (2.0 * (radius ** 2)))
    mask = (mask * intensity * 255.0)[:, :, np.newaxis]
    arr = np.clip(arr + mask, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def generate_synthetic_dataset(base_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Generates the controlled synthetic dataset with images and annotations."""
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    img_dir = base_dir / "images" / "synthetic"
    ann_dir = base_dir / "annotations" / "synthetic"
    img_dir.mkdir(parents=True, exist_ok=True)
    ann_dir.mkdir(parents=True, exist_ok=True)

    products = []

    # -------------------------------------------------------------
    # Product 01: FMCG Food Pouch (Basmati Rice) — Front & Back
    # -------------------------------------------------------------
    p01_front_lines = [
        ("ROYAL BASMATI RICE", "header", 22, (255, 255, 255)),
        ("Premium Aged Fragrant Grain", "text", 16, (60, 60, 60)),
        ("", "rule", 10, (0, 0, 0)),
        ("Net Quantity: 500 g", "text", 20, (20, 20, 20)),
        ("MRP: ₹149.00 (Incl. of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p01_front = render_label_canvas(650, 320, p01_front_lines)
    img_p01_front_path = img_dir / "prod_01_food_pouch_front.png"
    img_p01_front.save(img_p01_front_path)

    p01_back_lines = [
        ("STATUTORY INFORMATION", "header", 20, (255, 255, 255)),
        ("Manufactured By: Royal Foods India Pvt Ltd,", "text", 16, (30, 30, 30)),
        ("Plot 45, Sector 18, Gurugram, Haryana - 122015", "text", 16, (30, 30, 30)),
        ("Mfg Date: 03/2026", "text", 18, (20, 20, 20)),
        ("Best Before 12 Months from Packaging", "text", 18, (20, 20, 20)),
        ("Consumer Care: care@royalfoods.in, Tel: 1800-200-1122", "text", 16, (40, 40, 40)),
        ("Country of Origin: India", "text", 17, (30, 30, 30)),
    ]
    img_p01_back = render_label_canvas(680, 360, p01_back_lines)
    img_p01_back_path = img_dir / "prod_01_food_pouch_back.png"
    img_p01_back.save(img_p01_back_path)

    p01_annotation = {
        "product_id": "prod_01_food_pouch",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Plastic Pouch",
        "category": "Food & Grocery",
        "images": [
            {"image_id": "prod_01_front", "file_name": "prod_01_food_pouch_front.png", "role": "front"},
            {"image_id": "prod_01_back", "file_name": "prod_01_food_pouch_back.png", "role": "back"},
        ],
        "ground_truth": {
            "PRODUCT_NAME": "ROYAL BASMATI RICE",
            "MRP": "₹149.00",
            "NET_QUANTITY": "500 g",
            "MANUFACTURER": "Royal Foods India Pvt Ltd, Plot 45, Sector 18, Gurugram, Haryana - 122015",
            "PACKER": None,
            "IMPORTER": None,
            "MANUFACTURING_DATE": "03/2026",
            "PACKING_DATE": None,
            "EXPIRY_DATE": None,
            "BEST_BEFORE": "12 Months from Packaging",
            "CONSUMER_CARE": "care@royalfoods.in, Tel: 1800-200-1122",
            "COUNTRY_OF_ORIGIN": "India",
        }
    }
    with open(ann_dir / "prod_01_food_pouch.json", "w", encoding="utf-8") as f:
        json.dump(p01_annotation, f, indent=2)
    products.append(p01_annotation)

    # -------------------------------------------------------------
    # Product 02: Personal Care Carton (Face Wash) — Front, Back, Side
    # -------------------------------------------------------------
    p02_front_lines = [
        ("NIMBA HERBAL FACE WASH", "header", 22, (255, 255, 255)),
        ("Deep Cleansing Formula", "text", 16, (50, 50, 50)),
        ("", "rule", 10, (0, 0, 0)),
        ("Net Volume: 200 ml", "text", 20, (20, 20, 20)),
        ("MRP Rs. 299.00 (Incl. of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p02_front = render_label_canvas(650, 300, p02_front_lines)
    img_p02_front_path = img_dir / "prod_02_carton_front.png"
    img_p02_front.save(img_p02_front_path)

    p02_back_lines = [
        ("PRODUCT DETAILS", "header", 20, (255, 255, 255)),
        ("Manufactured by: Alpha Herbal Labs, Haridwar, Uttarakhand - 249401", "text", 16, (30, 30, 30)),
        ("Packed by: Beta Pack Solutions, Okhla, New Delhi - 110020", "text", 16, (30, 30, 30)),
        ("Date of Manufacture: 01/2026", "text", 18, (20, 20, 20)),
        ("Expiry Date: 12/2027", "text", 18, (20, 20, 20)),
    ]
    img_p02_back = render_label_canvas(680, 320, p02_back_lines)
    img_p02_back_path = img_dir / "prod_02_carton_back.png"
    img_p02_back.save(img_p02_back_path)

    p02_side_lines = [
        ("CUSTOMER SUPPORT & ORIGIN", "header", 18, (255, 255, 255)),
        ("Consumer Care: contact@nimbaherbal.com, Toll Free 1800-999-4444", "text", 15, (30, 30, 30)),
        ("Country of Origin: India", "text", 17, (20, 20, 20)),
    ]
    img_p02_side = render_label_canvas(650, 240, p02_side_lines)
    img_p02_side_path = img_dir / "prod_02_carton_side.png"
    img_p02_side.save(img_p02_side_path)

    p02_annotation = {
        "product_id": "prod_02_carton",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Cardboard Carton",
        "category": "Cosmetics & Personal Care",
        "images": [
            {"image_id": "prod_02_front", "file_name": "prod_02_carton_front.png", "role": "front"},
            {"image_id": "prod_02_back", "file_name": "prod_02_carton_back.png", "role": "back"},
            {"image_id": "prod_02_side", "file_name": "prod_02_carton_side.png", "role": "side"},
        ],
        "ground_truth": {
            "PRODUCT_NAME": "NIMBA HERBAL FACE WASH",
            "MRP": "Rs. 299.00",
            "NET_QUANTITY": "200 ml",
            "MANUFACTURER": "Alpha Herbal Labs, Haridwar, Uttarakhand - 249401",
            "PACKER": "Beta Pack Solutions, Okhla, New Delhi - 110020",
            "IMPORTER": None,
            "MANUFACTURING_DATE": "01/2026",
            "PACKING_DATE": None,
            "EXPIRY_DATE": "12/2027",
            "BEST_BEFORE": None,
            "CONSUMER_CARE": "contact@nimbaherbal.com, Toll Free 1800-999-4444",
            "COUNTRY_OF_ORIGIN": "India",
        }
    }
    with open(ann_dir / "prod_02_carton.json", "w", encoding="utf-8") as f:
        json.dump(p02_annotation, f, indent=2)
    products.append(p02_annotation)

    # -------------------------------------------------------------
    # Product 03: Beverage Bottle with Nutrition Distractors
    # -------------------------------------------------------------
    p03_front_lines = [
        ("MANGO DELIGHT PULP", "header", 22, (255, 255, 255)),
        ("100% Fruit Juice Beverage", "text", 16, (40, 40, 40)),
        ("Net Quantity: 1 L", "text", 20, (20, 20, 20)),
        ("MRP: ₹99.00 (Incl. of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p03_front = render_label_canvas(650, 300, p03_front_lines)
    img_p03_front_path = img_dir / "prod_03_bottle_front.png"
    img_p03_front.save(img_p03_front_path)

    p03_back_lines = [
        ("NUTRITION FACTS & DETAILS", "header", 20, (255, 255, 255)),
        ("Energy: 120 kcal per serving", "text", 16, (80, 80, 80)),
        ("Carbohydrates: 28 g | Total Sugar: 24 g", "text", 16, (80, 80, 80)),
        ("Protein: 1 g | Sodium: 15 mg", "text", 16, (80, 80, 80)),
        ("", "rule", 10, (0, 0, 0)),
        ("Manufactured By: Fresh Beverages Pvt Ltd, Pune, MH - 411001", "text", 16, (30, 30, 30)),
        ("Mfg Date: 02/2026", "text", 18, (20, 20, 20)),
        ("Best Before 6 Months from Mfd", "text", 18, (20, 20, 20)),
        ("Consumer Support: 1800-456-7890, support@freshbev.in", "text", 16, (30, 30, 30)),
        ("Country of Origin: India", "text", 17, (30, 30, 30)),
    ]
    img_p03_back = render_label_canvas(680, 420, p03_back_lines)
    img_p03_back_path = img_dir / "prod_03_bottle_back.png"
    img_p03_back.save(img_p03_back_path)

    p03_annotation = {
        "product_id": "prod_03_bottle",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Plastic PET Bottle",
        "category": "Beverages",
        "images": [
            {"image_id": "prod_03_front", "file_name": "prod_03_bottle_front.png", "role": "front"},
            {"image_id": "prod_03_back", "file_name": "prod_03_bottle_back.png", "role": "back"},
        ],
        "ground_truth": {
            "PRODUCT_NAME": "MANGO DELIGHT PULP",
            "MRP": "₹99.00",
            "NET_QUANTITY": "1 L",
            "MANUFACTURER": "Fresh Beverages Pvt Ltd, Pune, MH - 411001",
            "PACKER": None,
            "IMPORTER": None,
            "MANUFACTURING_DATE": "02/2026",
            "PACKING_DATE": None,
            "EXPIRY_DATE": None,
            "BEST_BEFORE": "6 Months from Mfd",
            "CONSUMER_CARE": "1800-456-7890, support@freshbev.in",
            "COUNTRY_OF_ORIGIN": "India",
        }
    }
    with open(ann_dir / "prod_03_bottle.json", "w", encoding="utf-8") as f:
        json.dump(p03_annotation, f, indent=2)
    products.append(p03_annotation)

    # -------------------------------------------------------------
    # Product 04: Imported Cookies Tin (Importer + Origin Denmark)
    # -------------------------------------------------------------
    p04_front_lines = [
        ("ROYAL DANISH COOKIES", "header", 22, (255, 255, 255)),
        ("Traditional Butter Biscuit Selection", "text", 16, (50, 50, 50)),
        ("Net Weight: 400 g", "text", 20, (20, 20, 20)),
        ("MRP: ₹450.00 (Inclusive of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p04_front = render_label_canvas(650, 300, p04_front_lines)
    img_p04_front_path = img_dir / "prod_04_tin_front.png"
    img_p04_front.save(img_p04_front_path)

    p04_back_lines = [
        ("IMPORT DECLARATION", "header", 20, (255, 255, 255)),
        ("Manufactured by: Copenhagen Baking Co, DK-1000 Denmark", "text", 16, (30, 30, 30)),
        ("Imported & Marketed by: Global Trade Importers India Ltd,", "text", 16, (30, 30, 30)),
        ("Fort, Mumbai, Maharashtra - 400001", "text", 16, (30, 30, 30)),
        ("Date of Import / Packing: 11/2025", "text", 18, (20, 20, 20)),
        ("Expiry Date: 11/2027", "text", 18, (20, 20, 20)),
        ("Consumer Care: 1800-888-3333, help@globaltrade.in", "text", 16, (30, 30, 30)),
        ("Country of Origin: Denmark", "text", 18, (20, 20, 20)),
    ]
    img_p04_back = render_label_canvas(680, 380, p04_back_lines)
    img_p04_back_path = img_dir / "prod_04_tin_back.png"
    img_p04_back.save(img_p04_back_path)

    p04_annotation = {
        "product_id": "prod_04_tin",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Metallic Tin",
        "category": "Confectionery & Bakery",
        "images": [
            {"image_id": "prod_04_front", "file_name": "prod_04_tin_front.png", "role": "front"},
            {"image_id": "prod_04_back", "file_name": "prod_04_tin_back.png", "role": "back"},
        ],
        "ground_truth": {
            "PRODUCT_NAME": "ROYAL DANISH COOKIES",
            "MRP": "₹450.00",
            "NET_QUANTITY": "400 g",
            "MANUFACTURER": "Copenhagen Baking Co, DK-1000 Denmark",
            "PACKER": None,
            "IMPORTER": "Global Trade Importers India Ltd, Fort, Mumbai, Maharashtra - 400001",
            "MANUFACTURING_DATE": None,
            "PACKING_DATE": "11/2025",
            "EXPIRY_DATE": "11/2027",
            "BEST_BEFORE": None,
            "CONSUMER_CARE": "1800-888-3333, help@globaltrade.in",
            "COUNTRY_OF_ORIGIN": "Denmark",
        }
    }
    with open(ann_dir / "prod_04_tin.json", "w", encoding="utf-8") as f:
        json.dump(p04_annotation, f, indent=2)
    products.append(p04_annotation)

    # -------------------------------------------------------------
    # Product 05: Failure Test A — Unreadable MRP (Severe Blur)
    # -------------------------------------------------------------
    p05_front_lines = [
        ("ORGANIC GREEN TEA", "header", 22, (255, 255, 255)),
        ("Pure Herbal Leaf Blend", "text", 16, (50, 50, 50)),
        ("Net Weight: 100 g", "text", 20, (20, 20, 20)),
        ("MRP: ₹199.00 (Incl. of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p05_clean = render_label_canvas(650, 300, p05_front_lines)
    img_p05_blurred = apply_blur(img_p05_clean, radius=6.0)  # Severe blur
    img_p05_path = img_dir / "prod_05_unreadable_mrp.png"
    img_p05_blurred.save(img_p05_path)

    p05_annotation = {
        "product_id": "prod_05_unreadable_mrp",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Plastic Pouch",
        "category": "Tea & Coffee",
        "images": [
            {"image_id": "prod_05_front", "file_name": "prod_05_unreadable_mrp.png", "role": "front"}
        ],
        "ground_truth": {
            "PRODUCT_NAME": "ORGANIC GREEN TEA",
            "MRP": "₹199.00",
            "NET_QUANTITY": "100 g",
            "MANUFACTURER": None,
            "PACKER": None,
            "IMPORTER": None,
            "MANUFACTURING_DATE": None,
            "PACKING_DATE": None,
            "EXPIRY_DATE": None,
            "BEST_BEFORE": None,
            "CONSUMER_CARE": None,
            "COUNTRY_OF_ORIGIN": None,
        },
        "expected_failure_states": {
            "MRP": "UNABLE_TO_VERIFY"
        }
    }
    with open(ann_dir / "prod_05_unreadable_mrp.json", "w", encoding="utf-8") as f:
        json.dump(p05_annotation, f, indent=2)
    products.append(p05_annotation)

    # -------------------------------------------------------------
    # Product 06: Failure Test B — Genuinely Missing MRP (NOT_FOUND)
    # -------------------------------------------------------------
    p06_front_lines = [
        ("WHOLE WHEAT FLOUR", "header", 22, (255, 255, 255)),
        ("Stone Ground Chakki Fresh", "text", 16, (50, 50, 50)),
        ("Net Weight: 5 kg", "text", 20, (20, 20, 20)),
        ("Mfg Date: 02/2026", "text", 18, (30, 30, 30)),
        ("Manufactured By: Golden Mills Ltd, Indore, MP - 452001", "text", 16, (30, 30, 30)),
        ("Country of Origin: India", "text", 17, (30, 30, 30)),
        # Crucially: NO MRP printed on label!
    ]
    img_p06 = render_label_canvas(650, 320, p06_front_lines)
    img_p06_path = img_dir / "prod_06_missing_mrp.png"
    img_p06.save(img_p06_path)

    p06_annotation = {
        "product_id": "prod_06_missing_mrp",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Paper / Poly Bag",
        "category": "Staples & Flour",
        "images": [
            {"image_id": "prod_06_front", "file_name": "prod_06_missing_mrp.png", "role": "front"}
        ],
        "ground_truth": {
            "PRODUCT_NAME": "WHOLE WHEAT FLOUR",
            "MRP": None,  # Genuinely absent!
            "NET_QUANTITY": "5 kg",
            "MANUFACTURER": "Golden Mills Ltd, Indore, MP - 452001",
            "PACKER": None,
            "IMPORTER": None,
            "MANUFACTURING_DATE": "02/2026",
            "PACKING_DATE": None,
            "EXPIRY_DATE": None,
            "BEST_BEFORE": None,
            "CONSUMER_CARE": None,
            "COUNTRY_OF_ORIGIN": "India",
        },
        "expected_failure_states": {
            "MRP": "NOT_FOUND"
        }
    }
    with open(ann_dir / "prod_06_missing_mrp.json", "w", encoding="utf-8") as f:
        json.dump(p06_annotation, f, indent=2)
    products.append(p06_annotation)

    # -------------------------------------------------------------
    # Product 07: Failure Test C — Glare Over MRP
    # -------------------------------------------------------------
    p07_front_lines = [
        ("CASHEW NUT PACK", "header", 22, (255, 255, 255)),
        ("Premium Whole Grade W240", "text", 16, (50, 50, 50)),
        ("Net Weight: 250 g", "text", 20, (20, 20, 20)),
        ("MRP: ₹350.00 (Incl. of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p07_clean = render_label_canvas(650, 300, p07_front_lines)
    # Put harsh glare directly over the MRP box area (x=180, y=190)
    img_p07_glare = apply_glare_hotspot(img_p07_clean, center_x=180, center_y=190, radius=90, intensity=0.95)
    img_p07_path = img_dir / "prod_07_glare_over_mrp.png"
    img_p07_glare.save(img_p07_path)

    p07_annotation = {
        "product_id": "prod_07_glare_over_mrp",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Glossy Pouch",
        "category": "Dry Fruits & Nuts",
        "images": [
            {"image_id": "prod_07_front", "file_name": "prod_07_glare_over_mrp.png", "role": "front"}
        ],
        "ground_truth": {
            "PRODUCT_NAME": "CASHEW NUT PACK",
            "MRP": "₹350.00",
            "NET_QUANTITY": "250 g",
            "MANUFACTURER": None,
            "PACKER": None,
            "IMPORTER": None,
            "MANUFACTURING_DATE": None,
            "PACKING_DATE": None,
            "EXPIRY_DATE": None,
            "BEST_BEFORE": None,
            "CONSUMER_CARE": None,
            "COUNTRY_OF_ORIGIN": None,
        }
    }
    with open(ann_dir / "prod_07_glare_over_mrp.json", "w", encoding="utf-8") as f:
        json.dump(p07_annotation, f, indent=2)
    products.append(p07_annotation)

    # -------------------------------------------------------------
    # Product 08: Failure Test D — False Currency Distractors
    # -------------------------------------------------------------
    p08_front_lines = [
        ("CRUNCHY OAT CEREAL", "header", 22, (255, 255, 255)),
        ("SUPER SAVER OFFER! SAVE ₹50 ON NEXT PACK", "text", 16, (180, 30, 30)),
        ("Cashback Offer: Up to ₹100 inside wrapper", "text", 16, (180, 30, 30)),
        ("Special Promo Discount ₹20 Applied", "text", 16, (180, 30, 30)),
        ("", "rule", 10, (0, 0, 0)),
        ("Net Weight: 400 g", "text", 20, (20, 20, 20)),
        ("MRP: ₹199.00 (Inclusive of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p08 = render_label_canvas(680, 340, p08_front_lines)
    img_p08_path = img_dir / "prod_08_price_distractors.png"
    img_p08.save(img_p08_path)

    p08_annotation = {
        "product_id": "prod_08_price_distractors",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Carton Box",
        "category": "Breakfast Cereals",
        "images": [
            {"image_id": "prod_08_front", "file_name": "prod_08_price_distractors.png", "role": "front"}
        ],
        "ground_truth": {
            "PRODUCT_NAME": "CRUNCHY OAT CEREAL",
            "MRP": "₹199.00",
            "NET_QUANTITY": "400 g",
            "MANUFACTURER": None,
            "PACKER": None,
            "IMPORTER": None,
            "MANUFACTURING_DATE": None,
            "PACKING_DATE": None,
            "EXPIRY_DATE": None,
            "BEST_BEFORE": None,
            "CONSUMER_CARE": None,
            "COUNTRY_OF_ORIGIN": None,
        }
    }
    with open(ann_dir / "prod_08_price_distractors.json", "w", encoding="utf-8") as f:
        json.dump(p08_annotation, f, indent=2)
    products.append(p08_annotation)

    # -------------------------------------------------------------
    # Product 09: Failure Test E — Quantity & Nutrition Distractors
    # -------------------------------------------------------------
    p09_front_lines = [
        ("PROTEIN BARS MULTIPACK", "header", 22, (255, 255, 255)),
        ("Pack of 6 Bars | Serving Size: 1 Bar (50g)", "text", 16, (60, 60, 60)),
        ("Calories: 210 kcal | Protein: 20 g", "text", 16, (60, 60, 60)),
        ("Carbohydrates: 25 g | Total Fat: 7 g", "text", 16, (60, 60, 60)),
        ("", "rule", 10, (0, 0, 0)),
        ("Net Weight: 300 g", "text", 20, (20, 20, 20)),
        ("MRP: ₹360.00 (Incl. of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p09 = render_label_canvas(680, 340, p09_front_lines)
    img_p09_path = img_dir / "prod_09_quantity_distractors.png"
    img_p09.save(img_p09_path)

    p09_annotation = {
        "product_id": "prod_09_quantity_distractors",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Cardboard Box",
        "category": "Health Foods",
        "images": [
            {"image_id": "prod_09_front", "file_name": "prod_09_quantity_distractors.png", "role": "front"}
        ],
        "ground_truth": {
            "PRODUCT_NAME": "PROTEIN BARS MULTIPACK",
            "MRP": "₹360.00",
            "NET_QUANTITY": "300 g",
            "MANUFACTURER": None,
            "PACKER": None,
            "IMPORTER": None,
            "MANUFACTURING_DATE": None,
            "PACKING_DATE": None,
            "EXPIRY_DATE": None,
            "BEST_BEFORE": None,
            "CONSUMER_CARE": None,
            "COUNTRY_OF_ORIGIN": None,
        }
    }
    with open(ann_dir / "prod_09_quantity_distractors.json", "w", encoding="utf-8") as f:
        json.dump(p09_annotation, f, indent=2)
    products.append(p09_annotation)

    # -------------------------------------------------------------
    # Product 10: Failure Test F — Date Distractors (Batch/Lic Nos)
    # -------------------------------------------------------------
    p10_front_lines = [
        ("AYURVEDIC HEALTH TONIC", "header", 22, (255, 255, 255)),
        ("Batch No: B987654 | FSSAI Lic No: 10019022009876", "text", 15, (60, 60, 60)),
        ("Drug Lic No: 25D/78/2021 | Barcode Ref: 890123456789", "text", 15, (60, 60, 60)),
        ("", "rule", 10, (0, 0, 0)),
        ("MFD: 04/2025", "text", 18, (20, 20, 20)),
        ("EXP: 04/2028", "text", 18, (20, 20, 20)),
        ("Net Content: 450 ml", "text", 20, (20, 20, 20)),
        ("MRP: ₹185.00 (Incl. of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p10 = render_label_canvas(680, 360, p10_front_lines)
    img_p10_path = img_dir / "prod_10_date_distractors.png"
    img_p10.save(img_p10_path)

    p10_annotation = {
        "product_id": "prod_10_date_distractors",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Glass Bottle Carton",
        "category": "Ayurveda & Health",
        "images": [
            {"image_id": "prod_10_front", "file_name": "prod_10_date_distractors.png", "role": "front"}
        ],
        "ground_truth": {
            "PRODUCT_NAME": "AYURVEDIC HEALTH TONIC",
            "MRP": "₹185.00",
            "NET_QUANTITY": "450 ml",
            "MANUFACTURER": None,
            "PACKER": None,
            "IMPORTER": None,
            "MANUFACTURING_DATE": "04/2025",
            "PACKING_DATE": None,
            "EXPIRY_DATE": "04/2028",
            "BEST_BEFORE": None,
            "CONSUMER_CARE": None,
            "COUNTRY_OF_ORIGIN": None,
        }
    }
    with open(ann_dir / "prod_10_date_distractors.json", "w", encoding="utf-8") as f:
        json.dump(p10_annotation, f, indent=2)
    products.append(p10_annotation)

    # -------------------------------------------------------------
    # Product 11: Multi-Panel Distributed Evidence
    # -------------------------------------------------------------
    p11_front_lines = [
        ("PREMIUM FILTER COFFEE", "header", 22, (255, 255, 255)),
        ("Net Weight: 500 g", "text", 20, (20, 20, 20)),
        ("MRP: ₹280.00 (Incl. of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p11_front = render_label_canvas(650, 260, p11_front_lines)
    img_p11_front_path = img_dir / "prod_11_coffee_front.png"
    img_p11_front.save(img_p11_front_path)

    p11_back_lines = [
        ("MANUFACTURER & CONSUMER CARE", "header", 20, (255, 255, 255)),
        ("Manufactured by: Malabar Coffee Co, Coorg, KA - 571201", "text", 16, (30, 30, 30)),
        ("Consumer Care: 1800-425-9999, care@malabarcoffee.in", "text", 16, (30, 30, 30)),
    ]
    img_p11_back = render_label_canvas(650, 240, p11_back_lines)
    img_p11_back_path = img_dir / "prod_11_coffee_back.png"
    img_p11_back.save(img_p11_back_path)

    p11_side_lines = [
        ("DATES & ORIGIN", "header", 20, (255, 255, 255)),
        ("Date of Manufacture: 01/2026", "text", 18, (20, 20, 20)),
        ("Best Before 9 Months from Packaging", "text", 18, (20, 20, 20)),
        ("Country of Origin: India", "text", 18, (20, 20, 20)),
    ]
    img_p11_side = render_label_canvas(650, 240, p11_side_lines)
    img_p11_side_path = img_dir / "prod_11_coffee_side.png"
    img_p11_side.save(img_p11_side_path)

    p11_annotation = {
        "product_id": "prod_11_coffee_distributed",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Vacuum Foil Pouch",
        "category": "Coffee",
        "images": [
            {"image_id": "prod_11_front", "file_name": "prod_11_coffee_front.png", "role": "front"},
            {"image_id": "prod_11_back", "file_name": "prod_11_coffee_back.png", "role": "back"},
            {"image_id": "prod_11_side", "file_name": "prod_11_coffee_side.png", "role": "side"},
        ],
        "ground_truth": {
            "PRODUCT_NAME": "PREMIUM FILTER COFFEE",
            "MRP": "₹280.00",
            "NET_QUANTITY": "500 g",
            "MANUFACTURER": "Malabar Coffee Co, Coorg, KA - 571201",
            "PACKER": None,
            "IMPORTER": None,
            "MANUFACTURING_DATE": "01/2026",
            "PACKING_DATE": None,
            "EXPIRY_DATE": None,
            "BEST_BEFORE": "9 Months from Packaging",
            "CONSUMER_CARE": "1800-425-9999, care@malabarcoffee.in",
            "COUNTRY_OF_ORIGIN": "India",
        }
    }
    with open(ann_dir / "prod_11_coffee_distributed.json", "w", encoding="utf-8") as f:
        json.dump(p11_annotation, f, indent=2)
    products.append(p11_annotation)

    # -------------------------------------------------------------
    # Product 12: Conflicting Prices Across Images (AMBIGUOUS)
    # -------------------------------------------------------------
    p12_front_lines = [
        ("SALTED ROASTED PEANUTS", "header", 22, (255, 255, 255)),
        ("Net Weight: 200 g", "text", 20, (20, 20, 20)),
        ("MRP: ₹45.00 (Incl. of all taxes)", "box", 20, (180, 20, 20)),
    ]
    img_p12_front = render_label_canvas(650, 240, p12_front_lines)
    img_p12_front_path = img_dir / "prod_12_peanuts_front.png"
    img_p12_front.save(img_p12_front_path)

    p12_back_lines = [
        ("PRODUCT SPECIFICATIONS", "header", 20, (255, 255, 255)),
        ("Net Weight: 200 g", "text", 20, (20, 20, 20)),
        ("MRP: ₹55.00 (Incl. of all taxes)", "box", 20, (180, 20, 20)),  # Conflict! ₹55 vs ₹45
    ]
    img_p12_back = render_label_canvas(650, 240, p12_back_lines)
    img_p12_back_path = img_dir / "prod_12_peanuts_back.png"
    img_p12_back.save(img_p12_back_path)

    p12_annotation = {
        "product_id": "prod_12_conflicting_prices",
        "dataset_type": "SYNTHETIC_CONTROLLED",
        "package_material": "Plastic Pouch",
        "category": "Snacks & Namkeen",
        "images": [
            {"image_id": "prod_12_front", "file_name": "prod_12_peanuts_front.png", "role": "front"},
            {"image_id": "prod_12_back", "file_name": "prod_12_peanuts_back.png", "role": "back"},
        ],
        "ground_truth": {
            "PRODUCT_NAME": "SALTED ROASTED PEANUTS",
            "MRP": "₹45.00",  # Conflicting with ₹55.00
            "NET_QUANTITY": "200 g",
            "MANUFACTURER": None,
            "PACKER": None,
            "IMPORTER": None,
            "MANUFACTURING_DATE": None,
            "PACKING_DATE": None,
            "EXPIRY_DATE": None,
            "BEST_BEFORE": None,
            "CONSUMER_CARE": None,
            "COUNTRY_OF_ORIGIN": None,
        },
        "expected_failure_states": {
            "MRP": "AMBIGUOUS"
        }
    }
    with open(ann_dir / "prod_12_conflicting_prices.json", "w", encoding="utf-8") as f:
        json.dump(p12_annotation, f, indent=2)
    products.append(p12_annotation)

    print(f"Generated {len(products)} synthetic controlled products in {base_dir}")
    return products


if __name__ == "__main__":
    generate_synthetic_dataset()
