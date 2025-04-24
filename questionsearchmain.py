import gspread
import pandas as pd
from openai import OpenAI
from config import GOOGLE_CREDENTIALS_FILE, OPENAI_API_KEY
import re

# 🔐 Init OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# 📥 Connect to Google Sheet
gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
sheet = gc.open("C0smos - AI Resources").sheet1
data = sheet.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0])

# 🔧 Clean headers
df.columns = [col.strip() for col in df.columns]

# 🏷️ Prepare tags
def extract_tags(text):
    tags = re.split(r',\s*', text) if text else []
    return [tag.strip().lower() for tag in tags]

df["all_tags"] = df["Main-tag"].fillna('') + ", " + df["Sub-tag"].fillna('')
df["all_tags"] = df["all_tags"].apply(extract_tags)

# 🎯 Match question to resources
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

# 🧠 Ask GPT
def generate_response(question, resources):
    resource_list = "\n".join(
        [f"- {row['Headline']} → {row['Button']}" for row in resources]
    )

    prompt = f"""
You are a UX assistant. A user has asked the following question:

"{question}"

Please do the following:
1. Provide a thoughtful, useful answer to the question (3-5 sentences).
2. Recommend the most relevant UX/Product resources from the following list:

Resources:
{resource_list}

Format output like this:
Answer:
[Your answer here]

Recommended Resources:
1. [Title] - [Link]
2. [Title] - [Link]
...
"""

    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800
    )

    return response.choices[0].message.content

# 🚀 Run it locally
if __name__ == "__main__":
    question = input("🔍 Enter a UX/Product question: ")
    relevant_resources = filter_relevant_resources(question, df)
    gpt_response = generate_response(question, relevant_resources)

    print("\n🧠 GPT Response:")
    print(gpt_response)
