This repository contains my solution for the HackRx Bill Extraction Challenge, which extracts structured bill line-items from raw invoice images using OCR and layout-aware parsing.
The solution exposes a fully compliant POST API endpoint as required in the task.

🚀 Overview

Given a bill/invoice image URL, the API:

Extracts item name, quantity, rate, and net amount

Handles table headers dynamically

Detects and skips summary/footer rows

Supports single-page bill extraction

Returns output in the exact HackRx response schema

Ensures no double-counting and no missed line-items

🧠 Approach

Image Retrieval

Downloads the document from the provided URL

OCR Processing (Tesseract)

Performs word-level OCR to obtain text + bounding boxes

Layout Reconstruction

Groups words into rows using Y-coordinate alignment

Identifies the table header dynamically

Determines column boundaries from header positions

Line-Item Extraction

Parses description, quantity, rate, and net amount

Cleans serial numbers (e.g., “92 Livi Tab” → “Livi Tab”)

Skips totals/footers to avoid double counting

API Output Generation

Produces response as per HackRx format

Includes pagewise_line_items, total_item_count, token_usage

🛠️ Tech Stack

FastAPI – REST API service

Tesseract OCR – Word-level text extraction

Python – Parsing and processing pipeline

🔗 API Endpoint

POST /extract-bill-data

Request
{
  "document": "https://example.com/bill_image.png"
}

Response (HackRx Format)
{
  "is_success": true,
  "token_usage": {
    "total_tokens": 0,
    "input_tokens": 0,
    "output_tokens": 0
  },
  "data": {
    "pagewise_line_items": [
      {
        "page_no": "1",
        "page_type": "Bill Detail",
        "bill_items": [
          {
            "item_name": "Livi 300mg Tab",
            "item_amount": 448.00,
            "item_rate": 32.00,
            "item_quantity": 14.00
          }
        ]
      }
    ],
    "total_item_count": 4
  }
}

▶️ Running Locally
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000


Open Swagger UI:
http://127.0.0.1:8000/docs



T