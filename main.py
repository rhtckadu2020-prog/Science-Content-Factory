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

client = genai.Client(api_key=GEMINI_KEY)
MODEL_ID = "gemini-2.5-flash" 

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(FIREBASE_JSON))
    firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})

def process_lesson(pdf_path, file_name):
    lesson_id = file_name.replace(".pdf", "").replace(" ", "_")
    output_dir = f"outputs/{lesson_id}"
    os.makedirs(output_dir, exist_ok=True) # Artifacts සඳහා ෆෝල්ඩරය සෑදීම

    print(f"Uploading PDF to Google Server: {file_name}...")
    try:
        uploaded_file = client.files.upload(file=pdf_path)
    except Exception as e:
        print(f"PDF Upload Error: {e}")
        return

    # 1. පාඩම කොටස් 10කට කැඩීම (සිංහලෙන්)
    print("Splitting PDF into 10 topics...")
    split_prompt = """
    Analyze this PDF and divide it into 10 logical sub-topics for teaching. 
    IMPORTANT: Return ONLY the list of 10 titles strictly in the Sinhala language.
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[uploaded_file, split_prompt]
        )
        sub_topics = response.text.split('\n')
        sub_topics =[t.strip() for t in sub_topics if t.strip()][:10]
        print(f"Sub-topics found: {sub_topics}")
    except Exception as e:
        print(f"Error splitting PDF: {e}")
        return

    lesson_data = {"title": lesson_id, "parts": {}}

    # 2. එක් එක් කොටස සඳහා Content සෑදීම (සිංහලෙන්)
    for i, topic in enumerate(sub_topics, 1):
        print(f"Generating Part {i}: {topic}...")
        content_prompt = f"""
        Based on the attached PDF, for the sub-topic '{topic}':
        1. Create a detailed Study Note.
        2. Create a Student Activity Note.
        3. Create a Video Script (Explain PDF facts + Activity Note).
        4. Create a styled HTML Note (with CSS).
        
        CRITICAL INSTRUCTION: Write EVERYTHING strictly in the Sinhala language. Do not use English.
        Format: Use exact markers [STUDY_NOTE], [ACTIVITY_NOTE],[VIDEO_SCRIPT], [HTML_NOTE].
        """
        
        try:
            res = client.models.generate_content(
                model=MODEL_ID,
                contents=[uploaded_file, content_prompt]
            )
            raw_text = res.text
            
            part_content = {
                "title": topic,
                "note": raw_text.split("[STUDY_NOTE]")[1].split("[ACTIVITY_NOTE]")[0].strip() if "[STUDY_NOTE]" in raw_text else "",
                "activity": raw_text.split("[ACTIVITY_NOTE]")[1].split("[VIDEO_SCRIPT]")[0].strip() if "[ACTIVITY_NOTE]" in raw_text else "",
                "script": raw_text.split("[VIDEO_SCRIPT]")[1].split("[HTML_NOTE]")[0].strip() if "[VIDEO_SCRIPT]" in raw_text else "",
                "html": raw_text.split("[HTML_NOTE]")[1].strip() if "[HTML_NOTE]" in raw_text else ""
            }
            
            lesson_data["parts"][f"part_{i}"] = part_content
            
            # --- GitHub Artifacts සඳහා ෆයිල් සේව් කිරීම ---
            # 1. HTML ෆයිල් එක
            if part_content["html"]:
                with open(f"{output_dir}/part_{i}_note.html", "w", encoding="utf-8") as f:
                    f.write(part_content["html"])
            
            # 2. Text ෆයිල් එක (Script සහ Note කියවීමට)
            text_content = f"මාතෘකාව: {topic}\n\n[අධ්‍යයන සටහන]\n{part_content['note']}\n\n[වීඩියෝ පිටපත]\n{part_content['script']}"
            with open(f"{output_dir}/part_{i}_text.txt", "w", encoding="utf-8") as f:
                f.write(text_content)
            
            time.sleep(10) # විරාමයක්
        except Exception as e:
            print(f"Error generating part {i}: {e}")

    # 3. MCQ Quiz සෑදීම (සිංහලෙන්)
    print("Generating Quizzes in Sinhala...")
    quiz_prompt = """
    Based on the entire PDF, generate 120 Multiple Choice Questions (MCQs).
    Divide them into 3 JSON arrays: 'easy' (40), 'medium' (40), 'hard' (40).
    Each MCQ must have: 'question', 'options' (4), 'answer_index' (0-3).
    
    CRITICAL INSTRUCTION: Write ALL questions and options strictly in the Sinhala language.
    Return ONLY the raw JSON format without markdown blocks.
    """
    try:
        quiz_res = client.models.generate_content(
            model=MODEL_ID,
            contents=[uploaded_file, quiz_prompt]
        )
        json_str = quiz_res.text.strip().replace("```json", "").replace("```", "")
        quiz_data = json.loads(json_str)
        lesson_data["quizzes"] = quiz_data
        
        # 3. JSON ෆයිල් එක සේව් කිරීම (Artifacts සඳහා)
        with open(f"{output_dir}/quizzes.json", "w", encoding="utf-8") as f:
            json.dump(quiz_data, f, indent=4, ensure_ascii=False)
            
    except Exception as e:
        print(f"Error generating quiz: {e}")

    # 4. Firebase වෙත යැවීම
    db.reference(f'lessons/{lesson_id}').set(lesson_data)
    print(f"Successfully Completed: {lesson_id}")

def main():
    input_folder = "inputs"
    output_folder = "outputs"
    
    # ප්‍රධාන outputs ෆෝල්ඩරය සෑදීම
    os.makedirs(output_folder, exist_ok=True)
    
    if not os.path.exists(input_folder): 
        print("Inputs folder not found!")
        return
        
    files = [f for f in os.listdir(input_folder) if f.endswith(".pdf")]
    if not files:
        print("No PDF files found in inputs folder!")
        return

    for file_name in files:
        process_lesson(os.path.join(input_folder, file_name), file_name)

if __name__ == "__main__":
    main()
