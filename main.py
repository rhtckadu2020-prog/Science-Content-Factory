import os
import json
import time
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, db

# --- 1. CONFIGURATION & SETUP ---
GEMINI_KEY = os.getenv("GEMINI_KEY_1")
FIREBASE_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT")
DB_URL = os.getenv("FIREBASE_DB_URL")

genai.configure(api_key=GEMINI_KEY)
# Gemini 2.0 Flash භාවිතා කිරීම
model = genai.GenerativeModel('gemini-1.5-flash')

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(FIREBASE_JSON))
    firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})

def process_lesson(pdf_path, file_name):
    lesson_id = file_name.replace(".pdf", "").replace(" ", "_")
    output_dir = f"outputs/{lesson_id}"
    os.makedirs(output_dir, exist_ok=True)

    # PDF එක Gemini වෙත Upload කිරීම
    print(f"Uploading PDF: {file_name}...")
    sample_file = genai.upload_file(path=pdf_path, display_name=file_name)
    
    # AI එකට මුලින්ම පාඩම කොටස් 10කට කඩන්න කියමු
    print("Splitting lesson into 10 parts...")
    split_prompt = "Analyze this PDF and divide it into 10 logical sub-topics for teaching. Return only the list of 10 titles."
    response = model.generate_content([sample_file, split_prompt])
    sub_topics = response.text.split('\n')
    sub_topics = [t.strip() for t in sub_topics if t.strip()][:10]

    lesson_data = {"title": lesson_id, "parts": {}}

    # එක් එක් කොටස සඳහා Content සෑදීම
    for i, topic in enumerate(sub_topics, 1):
        print(f"Generating Content for Part {i}: {topic}...")
        
        content_prompt = f"""
        Based on the attached PDF, for the sub-topic '{topic}':
        1. Create a detailed Study Note (Text).
        2. Create a Student Activity Note (Practical tasks).
        3. Create a Video Script: This must cover all scientific facts from the PDF for this section AND explain the activities in the Student Activity Note.
        4. Create a beautifully styled HTML Note (with CSS) for this section.
        
        Language: Use the same language as the PDF.
        Format: Return the output with clear markers like [STUDY_NOTE], [ACTIVITY_NOTE], [VIDEO_SCRIPT], [HTML_NOTE].
        """
        
        res = model.generate_content([sample_file, content_prompt])
        raw_text = res.text
        
        # දත්ත වෙන් කර ගැනීම (Simple Parsing)
        part_content = {
            "title": topic,
            "note": raw_text.split("[STUDY_NOTE]")[1].split("[ACTIVITY_NOTE]")[0] if "[STUDY_NOTE]" in raw_text else "",
            "activity": raw_text.split("[ACTIVITY_NOTE]")[1].split("[VIDEO_SCRIPT]")[0] if "[ACTIVITY_NOTE]" in raw_text else "",
            "script": raw_text.split("[VIDEO_SCRIPT]")[1].split("[HTML_NOTE]")[0] if "[VIDEO_SCRIPT]" in raw_text else "",
            "html": raw_text.split("[HTML_NOTE]")[1] if "[HTML_NOTE]" in raw_text else ""
        }
        
        # Firebase & Local Save
        lesson_data["parts"][f"part_{i}"] = part_content
        with open(f"{output_dir}/part_{i}_{topic}.html", "w", encoding="utf-8") as f:
            f.write(part_content["html"])

    # MCQ Quiz සෑදීම (Levels 3)
    print("Generating 120 MCQs (JSON)...")
    quiz_prompt = """
    Based on the entire PDF, generate 120 Multiple Choice Questions (MCQs).
    Divide them into 3 JSON arrays: 'easy' (40), 'medium' (40), 'hard' (40).
    Each MCQ must have: 'question', 'options' (4), 'answer_index' (0-3).
    Return ONLY the raw JSON.
    """
    quiz_res = model.generate_content([sample_file, quiz_prompt])
    try:
        # JSON එක පමණක් වෙන් කර ගැනීම
        json_str = quiz_res.text.strip().replace("```json", "").replace("```", "")
        quiz_data = json.loads(json_str)
        lesson_data["quizzes"] = quiz_data
        with open(f"{output_dir}/quizzes.json", "w", encoding="utf-8") as f:
            json.dump(quiz_data, f, indent=4)
    except:
        print("Quiz JSON parsing failed, saving raw text.")
        lesson_data["quizzes_raw"] = quiz_res.text

    # අවසාන දත්ත Firebase වෙත යැවීම
    db.reference(f'lessons/{lesson_id}').set(lesson_data)
    print(f"Successfully completed: {lesson_id}")

def main():
    input_folder = "inputs"
    if not os.path.exists(input_folder):
        os.makedirs(input_folder)
        return

    for file_name in os.listdir(input_folder):
        if file_name.endswith(".pdf"):
            process_lesson(os.path.join(input_folder, file_name), file_name)
            # Rate limit වැළැක්වීමට විරාමයක්
            time.sleep(10)

if __name__ == "__main__":
    main()
