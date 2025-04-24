# ai_search_api.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow Webflow to access your API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict to your Webflow domain later
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    question: str

@app.post("/ai-search")
async def ai_search(req: SearchRequest):
    # Drop in your logic from the GPT + Google Sheets script here
    # Return this structure:
    return {
        "answer": "Here’s your answer...",
        "resources": [
            {"title": "How to...", "link": "https://..."},
            {"title": "Another one", "link": "https://..."},
        ]
    }
