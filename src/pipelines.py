from pytesseract import Output
import requests
from io import BytesIO
from PIL import Image
import pytesseract
import shutil
import sys

# IMPORTANT: point to the executable, not just the folder.
# Make sure this path matches your actual installation.
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"



# On Windows use installed path; on Render/Linux auto-detect
if sys.platform.startswith("win"):
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")


# ------------------------
# 1. Download image
# ------------------------
def download_image(url: str) -> Image.Image:
    """
    Download an image from a URL and return it as a PIL Image.
    """
    headers = {
        # Pretend to be a normal browser
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    resp = requests.get(url, headers=headers, timeout=15)
    print("Status:", resp.status_code)
    print("Content-Type:", resp.headers.get("Content-Type"))

    resp.raise_for_status()

    img = Image.open(BytesIO(resp.content)).convert("RGB")
    return img


# ------------------------
# 2. OCR helpers
# ------------------------
def run_ocr(img: Image.Image) -> str:
    """
    Raw text OCR (kept for debugging).
    """
    text = pytesseract.image_to_string(img)
    return text


def run_ocr_with_boxes(img: Image.Image):
    """
    Returns Tesseract's word-level data: text + positions.
    """
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    return data


# ------------------------
# 3. Group OCR words into rows
# ------------------------
def group_into_rows(ocr_data, y_threshold: int = 10):
    """
    Group words into rows based on their 'top' coordinate.
    Returns: list of rows, each row = list of (x, text) tuples.
    """
    rows = []
    current_row = []
    last_y = None

    n = len(ocr_data["text"])
    for i in range(n):
        text = ocr_data["text"][i].strip()
        if not text:
            continue

        y = ocr_data["top"][i]
        x = ocr_data["left"][i]

        if last_y is None or abs(y - last_y) <= y_threshold:
            current_row.append((x, text))
        else:
            rows.append(current_row)
            current_row = [(x, text)]
        last_y = y

    if current_row:
        rows.append(current_row)

    # sort each row by x (left to right)
    sorted_rows = []
    for row in rows:
        sorted_rows.append(sorted(row, key=lambda t: t[0]))
    return sorted_rows


# ------------------------
# 4. Find header row & column boundaries
# ------------------------
def find_header_and_columns(rows):
    """
    Find the table header row and approximate column boundaries based on x-coordinate.
    Returns: (header_index, boundaries_dict)
    boundaries_dict keys: 'desc_max', 'qty_max', 'rate_max'
    """
    header_index = None
    header_row = None

    # 1) Find header row
    for idx, row in enumerate(rows):
        line = " ".join([t[1] for t in row]).lower()
        # Works for headers like:
        # "Sl# Description Cpt Code Date Qty Rate Gross Amount Discount"
        if ("description" in line and "qty" in line and "rate" in line) or \
           ("qty" in line and "net" in line):
            header_index = idx
            header_row = row
            break

    if header_row is None:
        print("No header row detected.")
        return None, None  # no header found

    # 2) Approximate column x positions using header words
    desc_x = qty_x = rate_x = net_x = None

    for x, text in header_row:
        t = text.lower()
        if "desc" in  t:
            desc_x = x
        elif "qty" in t:
            qty_x = x
        elif "rate" in t:
            rate_x = x
        elif "net" in t or "gross" in t:  # allow gross/net as last column-ish
            net_x = x

    boundaries = {}

    xs = [v for v in [desc_x, qty_x, rate_x, net_x] if v is not None]
    xs_sorted = sorted(xs)

    # Create ranges: [start, end) for each column
    # We assume order: description, qty, rate, net/gross
    if len(xs_sorted) >= 2:
        boundaries["desc_max"] = (xs_sorted[0] + xs_sorted[1]) / 2
    if len(xs_sorted) >= 3:
        boundaries["qty_max"] = (xs_sorted[1] + xs_sorted[2]) / 2
    if len(xs_sorted) >= 4:
        boundaries["rate_max"] = (xs_sorted[2] + xs_sorted[3]) / 2
    # net/gross column: anything >= last boundary

    print("Header row index:", header_index)
    print("Boundaries:", boundaries)

    return header_index, boundaries


# ------------------------
# 5. Row parsing helpers
# ------------------------
def try_parse_float(s: str):
    s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return None


def clean_description(desc: str) -> str:
    """
    Remove leading serial number from description if present.
    e.g. "92 Livi 300mg Tab" -> "Livi 300mg Tab"
    """
    parts = desc.split()
    if parts and parts[0].isdigit():
        parts = parts[1:]
    return " ".join(parts).strip()


def parse_items_from_rows(rows, header_idx, boundaries):
    """
    Given full rows, a header index and column boundaries, extract bill_items.
    """
    bill_items = []
    if header_idx is None or boundaries is None:
        return bill_items

    desc_max = boundaries.get("desc_max", None)
    qty_max = boundaries.get("qty_max", None)
    rate_max = boundaries.get("rate_max", None)

    for row in rows[header_idx + 1:]:
        texts = [t[1] for t in row]
        line = " ".join(texts).lower()

        # skip footer / totals
        if "category total" in line:
            continue
        if "page" in line and "of" in line:
            break
        if "printed on" in line:
            break

        desc_tokens = []
        qty_tokens = []
        rate_tokens = []
        net_tokens = []

        for x, text in row:
            if not text.strip():
                continue

            if desc_max is not None and x < desc_max:
                desc_tokens.append(text)
            elif qty_max is not None and x < qty_max:
                qty_tokens.append(text)
            elif rate_max is not None and x < rate_max:
                rate_tokens.append(text)
            else:
                net_tokens.append(text)

        desc = " ".join(desc_tokens).strip()
        qty_str = "".join(qty_tokens).strip()
        rate_str = "".join(rate_tokens).strip()

        # For the "Gross Amount / Discount" area:
        # pick the *first numeric token* as item_amount and ignore discount.
        net_value = None
        for t in net_tokens:
            v = try_parse_float(t)
            if v is not None:
                net_value = v
                break

        # parse numeric fields
        qty = try_parse_float(qty_str)
        rate = try_parse_float(rate_str)
        net = net_value

        # basic sanity: we at least want a description and a net amount
        desc = clean_description(desc)
        if not desc or net is None:
            continue

        item = {
            "item_name": desc,
            "item_amount": net,
            "item_rate": rate if rate is not None else net,
            "item_quantity": qty if qty is not None else 1.0
        }
        bill_items.append(item)

    return bill_items


# ------------------------
# 6. Main entry: used by FastAPI
# ------------------------
def extract_bill_info_from_url(url: str) -> dict:
    """
    Main function called from FastAPI:
    - Download image
    - Run OCR with boxes
    - Group into rows
    - Find header and parse line items
    - Return JSON in required format
    """
    img = download_image(url)
    ocr_data = run_ocr_with_boxes(img)
    rows = group_into_rows(ocr_data)

    # Optional preview of first few rows:
    print("===== ROWS PREVIEW =====")
    for r in rows[:20]:
        print(" ".join([t[1] for t in r]))
    print("===== END ROWS PREVIEW =====")

    header_idx, boundaries = find_header_and_columns(rows)
    bill_items = parse_items_from_rows(rows, header_idx, boundaries)

    # Debug: print a few parsed items
    print("Parsed items:")
    for item in bill_items[:10]:
        print(item)

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
