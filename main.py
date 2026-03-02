import os
import json
import time
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, db
from google.api_core import exceptions

# --- 1. CONFIGURATION & SETUP ---
GEMINI_KEY = os.getenv("GEMINI_KEY_1")
FIREBASE_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT")
DB_URL = os.getenv("FIREBASE_DB_URL")

genai.configure(api_key=GEMINI_KEY)
# වඩාත් ස්ථාවර 1.5 Flash මාදිලිය භාවිතා කිරීම
model = genai.GenerativeModel('gemini-1.5-flash')

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(FIREBASE_JSON))
    firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})

def safe_generate_content(parts):
    """Rate limit එකක් ආවොත් නැවත උත්සාහ කරන ශ්‍රිතය"""
    for i in range(3):  # උපරිම 3 වතාවක් උත්සාහ කරයි
        try:
            return model.generate_content(parts)
        except exceptions.ResourceExhausted:
            print(f"Quota පිරී ඇත. තත්පර 60ක් රැඳී සිටිනවා... (Attempt {i+1})")
            time.sleep(60)
    return None

def process_lesson(pdf_path, file_name):
    lesson_id = file_name.replace(".pdf", "").replace(" ", "_")
    output_dir = f"outputs/{lesson_id}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Uploading PDF: {file_name}...")
    sample_file = genai.upload_file(path=pdf_path, display_name=file_name)
    
    print("Splitting lesson into 10 parts...")
    split_prompt = "Analyze this PDF and divide it into 10 logical sub-topics for teaching. Return only the list of 10 titles."
    response = safe_generate_content([sample_file, split_prompt])
    
    if not response: return
    
    sub_topics = response.text.split('\n')
    sub_topics = [t.strip() for t in sub_topics if t.strip()][:10]

    lesson_data = {"title": lesson_id, "parts": {}}

    for i, topic in enumerate(sub_topics, 1):
        print(f"Generating Content for Part {i}: {topic}...")
        content_prompt = f"""
        Based on the attached PDF, for the sub-topic '{topic}':
        1. Create a detailed Study Note (Text).
        2. Create a Student Activity Note (Practical tasks).
        3. Create a Video Script: This must cover all scientific facts from the PDF for this section AND explain the activities in the Student Activity Note.
        4. Create a beautifully styled HTML Note (with CSS) for this section.
        Format: Return the output with clear markers like [STUDY_NOTE], [ACTIVITY_NOTE], [VIDEO_SCRIPT], [HTML_NOTE].
        """
        
        res = safe_generate_content([sample_file, content_prompt])
        if not res: continue
        
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
        time.sleep(10) # Request අතර විරාමයක්

    # Quiz සෑදීම
    print("Generating Quizzes...")
    quiz_prompt = "Generate 120 MCQs in JSON format (easy, medium, hard) based on the PDF."
    quiz_res = safe_generate_content([sample_file, quiz_prompt])
    if quiz_res:
        lesson_data["quizzes_raw"] = quiz_res.text

    db.reference(f'lessons/{lesson_id}').set(lesson_data)
    print(f"Successfully completed: {lesson_id}")

def main():
    input_folder = "inputs"
    for file_name in os.listdir(input_folder):
        if file_name.endswith(".pdf"):
            process_lesson(os.path.join(input_folder, file_name), file_name)

if __name__ == "__main__":
    main()
