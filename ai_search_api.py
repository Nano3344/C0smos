from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from google.oauth2.service_account import Credentials
import base64
import json
import gspread
import pandas as pd
import os
import re
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.c0smos.com"],
    allow_credentials=True,
    allow_methods=["*"],  # ← Just use "*" to support preflight OPTIONS requests
    allow_headers=["*"],
)

# ✅ Setup your environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")

client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ Load resources from Google Sheets
google_json_base64 = os.getenv("GOOGLE_JSON_BASE64")
google_json = base64.b64decode(google_json_base64).decode('utf-8')
info = json.loads(google_json)

creds = Credentials.from_service_account_info(info, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])

gc = gspread.authorize(creds)
sheet = gc.open("C0smos - AI Resources").sheet1
data = sheet.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0])

# ✅ Prepare tags for filtering
def extract_tags(text):
    tags = re.split(r',\s*', text) if text else []
    return [tag.strip().lower() for tag in tags]

df["all_tags"] = df["Main-tag"].fillna('') + ", " + df["Sub-tag"].fillna('')
df["all_tags"] = df["all_tags"].apply(extract_tags)

# ✅ Filter relevant resources
def filter_relevant_resources(question, df, max_matches=50):
    question = question.lower()
    matched_rows = []

    for _, row in df.iterrows():
        tags = row["all_tags"]
        if any(tag in question for tag in tags):
            matched_rows.append(row)

    if len(matched_rows) == 0:
        matched_rows = df.sample(n=min(max_matches, len(df))).to_dict("records")
    else:
        matched_rows = matched_rows[:max_matches]

    return matched_rows

# ✅ Generate GPT answer
def generate_response(question, resources):
    resource_list = "\n".join(
        [f"- {row['Headline']} → {row['Button']}" for row in resources]
    )

    prompt = f"""
You are the best UX/Product Expert in the world. Answer the user's question thoughtfully, and recommend relevant resources.

Question: {question}

Resources:
{resource_list}

Format:
Answer: [your thoughtful answer here]

Recommended Resources:
1. [Title] - [Link]
2. [Title] - [Link]
"""

    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800
    )

    return response.choices[0].message.content

# ✅ API Endpoint
@app.post("/ai-search")
async def ai_search(request: Request):
    body = await request.json()
    question = body.get("question")

    relevant_resources = filter_relevant_resources(question, df)
    resource_list = "\n".join(
        [f"- {row['Headline']} → {row['Button']}" for row in relevant_resources]
    )


    prompt = f"""
You are the best UX/Product Expert in the world. Answer the user's question thoughtfully, and recommend relevant resources.

Question: {question}

Resources:
{resource_list}

Format:
Answer: [your thoughtful answer here]

Recommended Resources:
1. [Title] - [Link]
2. [Title] - [Link]
"""

    def generate_chunks():
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            max_tokens=800,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                yield delta.content

    return StreamingResponse(generate_chunks(), media_type="text/plain")


@app.post("/ai-search-resources")
async def ai_search_resources(request: Request):
    body = await request.json()
    question = body.get("question")

    relevant_resources = filter_relevant_resources(question, df)

    formatted_resources = []
    for row in relevant_resources[:5]:
        formatted_resources.append({
            "title": row.get("Headline", "").strip(),
            "link": row.get("Button", "").strip(),
            "category": row.get("Category", "").strip(),
            "author": row.get("Author", "").strip()
        })

    return JSONResponse(content={"resources": formatted_resources})



