import requests
from io import BytesIO
from PIL import Image
import pytesseract

# If you're on Windows, set the path to tesseract.exe like this:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def download_image(url: str) -> Image.Image:
    """
    Download image from a URL and return as PIL Image.
    """
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content)).convert("RGB")
    return img

def run_ocr(img: Image.Image) -> str:
    """
    Run OCR on the image and return raw text.
    """
    text = pytesseract.image_to_string(img)
    return text

def extract_bill_info_from_url(url: str) -> dict:
    """
    For now:
    - Download the image
    - Run OCR
    - Print OCR text (for debugging)
    - Still return dummy JSON in correct structure
    """
    img = download_image(url)
    text = run_ocr(img)

    # TEMP: print OCR to server logs so you can inspect
    print("===== OCR OUTPUT START =====")
    print(text)
    print("===== OCR OUTPUT END =======")

    # TODO: later parse `text` into items

    # Dummy data kept for now so API always returns valid response
    bill_items = [
        {
            "item_name": "Dummy from OCR",
            "item_amount": 100.00,
            "item_rate": 100.00,
            "item_quantity": 1.00
        }
    ]

    total_item_count = len(bill_items)
    reconciled_amount = sum(item["item_amount"] for item in bill_items)

    result = {
        "is_success": True,
        "data": {
            "pagewise_line_items": [
                {
                    "page_no": "1",
                    "bill_items": bill_items
                }
            ],
            "total_item_count": total_item_count,
            "reconciled_amount": reconciled_amount
        }
    }
    return result
