from dataclasses import asdict

from fastapi import FastAPI, HTTPException
import requests

from lab2.task2.common import download, extract_page
from lab3.schemas import PagePayload, ParseRequest


app = FastAPI(title="BookCrossing parser service — LR3")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/parse", response_model=PagePayload)
def parse_page(data: ParseRequest) -> PagePayload:
    try:
        return PagePayload.model_validate(asdict(extract_page(data.url, download(data.url))))
    except (requests.RequestException, ValueError) as error:
        raise HTTPException(status_code=502, detail="Could not download or parse the source page") from error
