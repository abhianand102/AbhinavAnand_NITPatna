from fastapi import FastAPI
from pydantic import BaseModel
from pipelines import extract_bill_info_from_url

app = FastAPI()


class RequestBody(BaseModel):
    document: str   # URL of the bill image


@app.post("/extract-bill-data")
def extract_data(body: RequestBody):
    """
    Main API — returns structured bill items in EXACT Datathon format.
    """
    try:
        result = extract_bill_info_from_url(body.document)
        return result
    except Exception as exc:
        # Follow Datathon error schema as closely as possible
        return {
            "is_success": False,
            "token_usage": {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0
            },
            "data": None
        }