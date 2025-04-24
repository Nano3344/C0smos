import gspread
import pandas as pd
from openai import OpenAI
import os
from dotenv import load_dotenv

# =========================
# 🔑 CONFIG
# =========================
GOOGLE_CREDENTIALS_FILE = "uxverse-jsonkey.json"
SHEET_NAME = "UXverse Resources"
WORKSHEET_NAME = "Articles"

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# 📥 LOAD RESOURCES
# =========================
def load_resources_from_sheet():
    gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
    sheet = gc.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

    data = sheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])

    # Convert to list of dicts
    resources = []
    for _, row in df.iterrows():
        resources.append({
            "title": row.get("Headline", ""),
            "link": row.get("Button", ""),
            "main_tag": row.get("Main-tag", ""),
            "sub_tag": row.get("Sub-tag", ""),
            "summary": row.get("General Summary", "")
        })
    return resources

# =========================
# 🤖 ASK GPT TO ANSWER + MATCH
# =========================
def generate_answer_with_recommendations(question, resources):
    formatted_resources = "\n\n".join([
        f"Title: {r['title']}\nTags: {r['main_tag']} | {r['sub_tag']}\nSummary: {r['summary']}\nLink: {r['link']}"
        for r in resources
    ])

    prompt = f"""
A UX designer asked the following question:

**{question}**

First, provide a helpful, clear, and practical answer in 2-3 paragraphs.

Then, based on the resource list below, recommend up to 5 links that would help answer this question. Include the title and the link for each.

Resources:
{formatted_resources}
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt.strip()}],
        temperature=0.7,
        max_tokens=20
    )

    return response.choices[0].message.content.strip()

# =========================
# 🚀 MAIN FLOW
# =========================
def main():
    print("🔍 Question-Based UX Search 🔥")
    question = input("Enter your question: ")

    print("\n📥 Loading resources...")
    resources = load_resources_from_sheet()

    print("🧠 Asking GPT for answer + matches...")
    response = generate_answer_with_recommendations(question, resources)

    print("\n✨ Result:\n")
    print(response)

if __name__ == "__main__":
    main()
