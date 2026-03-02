import os
import json
import time
from google import genai
import firebase_admin
from firebase_admin import credentials, db

# --- 1. SETUP ---
GEMINI_KEY = os.getenv("GEMINI_KEY_1")
FIREBASE_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT")
DB_URL = os.getenv("FIREBASE_DB_URL")

# අලුත් Client එක සෑදීම
client = genai.Client(api_key=GEMINI_KEY)

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(FIREBASE_JSON))
    firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})

def get_best_model():
    """ඔබේ Key එකට වැඩ කරන හොඳම Flash model එක සොයා ගැනීම"""
    try:
        # දැනට පාවිච්චි කළ හැකි models ලැයිස්තුව ලබා ගැනීම
        models = client.models.list()
        for m in models:
            # Flash model එකක් සහ generateContent පුළුවන් එකක් තෝරා ගැනීම
            if "flash" in m.name.lower() and "generateContent" in m.supported_methods:
                print(f"Using Model: {m.name}")
                return m.name
    except Exception as e:
        print(f"Error listing models: {e}")
    return "gemini-1.5-flash" # Default එකක් ලෙස

MODEL_ID = get_best_model()

def process_lesson(pdf_path, file_name):
    lesson_id = file_name.replace(".pdf", "").replace(" ", "_")
    output_dir = f"outputs/{lesson_id}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Processing PDF: {file_name}...")
    
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    # 1. පාඩම කොටස් 10කට කැඩීම
    split_prompt = "Analyze this PDF and divide it into 10 logical sub-topics for teaching. Return only the list of 10 titles."
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[split_prompt, {"inline_data": {"data": pdf_data, "mime_type": "application/pdf"}}]
        )
        sub_topics = response.text.split('\n')
        sub_topics = [t.strip() for t in sub_topics if t.strip()][:10]
        print(f"Sub-topics: {sub_topics}")
    except Exception as e:
        print(f"Error splitting PDF: {e}")
        return

    lesson_data = {"title": lesson_id, "parts": {}}

    # 2. එක් එක් කොටස සඳහා Content සෑදීම
    for i, topic in enumerate(sub_topics, 1):
        print(f"Generating Part {i}: {topic}...")
        content_prompt = f"""
        Based on the attached PDF, for the sub-topic '{topic}':
        1. Create a detailed Study Note.
        2. Create a Student Activity Note.
        3. Create a Video Script (Explain PDF facts + Activity Note).
        4. Create a styled HTML Note (with CSS).
        Format: Use markers [STUDY_NOTE], [ACTIVITY_NOTE], [VIDEO_SCRIPT], [HTML_NOTE].
        """
        
        try:
            res = client.models.generate_content(
                model=MODEL_ID,
                contents=[content_prompt, {"inline_data": {"data": pdf_data, "mime_type": "application/pdf"}}]
            )
            raw_text = res.text
            
            part_content = {
                "title": topic,
                "note": raw_text.split("[STUDY_NOTE]")[1].split("[ACTIVITY_NOTE]")[0] if "[STUDY_NOTE]" in raw_text else "",
                "activity": raw_text.split("[ACTIVITY_NOTE]")[1].split("[VIDEO_SCRIPT]")[0] if "[ACTIVITY_NOTE]" in raw_text else "",
                "script": raw_text.split("[VIDEO_SCRIPT]")[1].split("[HTML_NOTE]")[0] if "[VIDEO_SCRIPT]" in raw_text else "",
                "html": raw_text.split("[HTML_NOTE]")[1] if "[HTML_NOTE]" in raw_text else ""
            }
            
            lesson_data["parts"][f"part_{i}"] = part_content
            with open(f"{output_dir}/part_{i}.html", "w", encoding="utf-8") as f:
                f.write(part_content["html"])
            
            time.sleep(10) # Rate limit පාලනයට
        except Exception as e:
            print(f"Error generating part {i}: {e}")

    # 3. Firebase Update
    db.reference(f'lessons/{lesson_id}').set(lesson_data)
    print(f"Successfully Completed: {lesson_id}")

def main():
    input_folder = "inputs"
    if not os.path.exists(input_folder): return
    files = [f for f in os.listdir(input_folder) if f.endswith(".pdf")]
    for file_name in files:
        process_lesson(os.path.join(input_folder, file_name), file_name)

if __name__ == "__main__":
    main()
