from fastapi import FastAPI
from pydantic import BaseModel
from pipeline import extract_bill_info_from_url

app = FastAPI()

class RequestBody(BaseModel):
    document: str  # URL of the bill image

@app.post("/predict")
def predict(body: RequestBody):
    try:
        result = extract_bill_info_from_url(body.document)
        return result
    except Exception as e:
        # If anything goes wrong, return a structured  error
        return {
            "is_success": False,
            "data": None,
            "error": str(e)
         }
