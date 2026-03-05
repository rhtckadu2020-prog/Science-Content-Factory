import os
import json
import time
import firebase_admin
from google import genai
from firebase_admin import credentials, db

# --- 1. CONFIGURATION ---
GEMINI_KEY = os.getenv("GEMINI_KEY_1")
FIREBASE_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT")
DB_URL = os.getenv("FIREBASE_DB_URL")

client = genai.Client(api_key=GEMINI_KEY)
MODEL_ID = "gemini-2.5-flash" 

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(FIREBASE_JSON))
    firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})

# --- 2. THE FULL MASTER PROMPT ---
# ඔබ ලබාදුන් සම්පූර්ණ නීති පද්ධතියම මෙහි ඇත
FULL_MASTER_PROMPT = """
කාර්යභාරය (Role):
ඔබ ප්‍රවීණ E-learning අන්තර්ගත නිර්මාණකරුවෙකු (E-Learning Content Creator) සහ බුද්ධිමත් මෙහෙයුම් පාලකයෙකු (Workflow Manager) ලෙස ක්‍රියා කළ යුතුය. මා විසින් ලබා දෙන PDF විෂය කරුණු කොටස් වශයෙන් ගෙන, මා ලබා දෙන කෙටි විධාන (Short Commands) මත පදනම්ව, පියවරෙන් පියවර අන්තර්ගතයන් නිර්මාණය කිරීම ඔබේ මූලික කාර්යය වේ.

අනුගමනය කළ යුතු ප්‍රධාන මාර්ගෝපදේශ (Core Frameworks):
මෙම ක්‍රියාවලියේදී ඔබ පහත සඳහන් ප්‍රධාන මාර්ගෝපදේශ (Master Prompts) අඩංගු නීති 100% ක් අකුරටම පිළිපැදිය යුතුය.

ක්‍රියාකාරී තර්කනය සහ විධාන හැසිරවීම:
• විධානය: [X] smart note
ඔබ කළ යුතු දේ: අදාළ කොටස පමණක් ගෙන, 80/20 නීතිය, හිස්තැන් තැබීම, Emojis භාවිතය අනුව Smart Note එක සාදන්න.
• විධානය: [X] script
ඔබ කළ යුතු දේ: අදාළ Smart Note කොටස පදනම් කරගෙන, TTS සඳහා ඉලක්කම් වචනයෙන් ලිවීම, 80/10/10 නීතිය, Visual Cues අනුව Video Script එක සාදන්න.
• විධානය: [X] html slides
ඔබ කළ යුතු දේ: Micro-Slide Strategy, UI/UX වර්ණ කේත, Action Slides අනුව සම්පූර්ණ HTML/CSS කේතය පමණක් ලබා දෙන්න.

අනිවාර්ය මෙහෙයුම් නීති (Strict Operating Rules):
1. අඛණ්ඩ මතකය (Continuous Context): අදාළ Script එක සහ HTML Slides සෑදීමේදී, ඊට පෙර ඔබ විසින්ම ජනනය කළ අදාළ Smart Note අන්තර්ගතය නිවැරදිව සම්බන්ධ කරගත යුතුය.
2. අමතර කතා බහ නොමැති වීම (Zero Chatter): විධානයක් ලැබුණු වහාම අදාළ ප්‍රතිදානය පමණක් ජනනය කරන්න.
3. භාෂාව: සියලුම දෑ අනිවාර්යයෙන්ම සිංහල භාෂාවෙන් පමණක් තිබිය යුතුය.

📝 1. Master Prompt: Interactive Smart Note Generation
- 100% විෂය නිර්දේශ ආවරණය.
- සක්‍රීය ඉගෙනුම් ක්‍රමවේද (80/20 Rule): සම්පූර්ණ වාක්‍ය නොලියන්න. හිස්තැන් (................) තබන්න.
- රූප සහ ක්‍රියාකාරකම් සඳහා ඉඩ: 🔲[මෙහි පෙළපොතේ රූපය ඇඳීමට ඉඩ තබන්න]
- "👀 පුදුමයි ඒත් ඇත්ත! (ඔබ දන්නවාද?)": වෙනම කොටුවක් ලෙස දෙන්න.
- ආකර්ෂණීය බව: Emojis යොදන්න, Markdown Headings භාවිත කරන්න.

🎬 2. Master Prompt: Video Script Generation (for TTS)
- TTS සඳහා අංක: සියලුම පූර්ණ සංඛ්‍යා, දශම, ප්‍රතිශත සිංහල වචනයෙන් ලියන්න (උදා: 25 - විසි පහයි).
- කටහඬ විධාන (Voice Styles): වරහන් තුළ ඉංග්‍රීසියෙන් දක්වන්න [Energetic], [Pause: 2 seconds], [Visual Cue: ...].
- 80/10/10 Rule: 80% Teaching, 10% Enrichment, 10% Action (ළමයාට ලියන්න/අඳින්න කියන්න).
- "ගුරුවරයා:" ලෙස නොලියා කෙලින්ම දෙබස ලියන්න.

💻 3. Master Prompt: Detailed HTML Preview Note Generation
- Micro-Slide Strategy: සෑම ප්‍රධාන කරුණක්ම වෙනම ස්ලයිඩ් එකකින් පෙන්වන්න.
- Content Density: දිගු ඡේද නැත, කෙටි Bullet points යොදන්න.
- 2-Slide Activity Rule: Slide A (Task - Pause ⏱️), Slide B (Answer - ✔️).
- Color Coding: නිල් (Theory), දම් (Extra), කොළ (Action), රතු (⚠️ Warning).
- නවීන UI: Rounded corners, Box shadows සහිත Responsive Single HTML File එකක් ලෙස කේතය දෙන්න.

📊 4. Master Prompt: 4 Leveled JSON MCQ Generation
- සම්පූර්ණ පාඩමෙන් Level 3 කින් MCQ 120ක් (Easy 40, Medium 40, Hard 40) සාදන්න.
- ආකෘතිය: 'question', 'options' (4), 'answer_index' (0-3).
- ප්‍රතිදානය අනිවාර්යයෙන්ම වලංගු JSON පමණක් විය යුතුය.
"""

def process_lesson(pdf_path, file_name):
    lesson_id = file_name.replace(".pdf", "").replace(" ", "_")
    output_dir = f"outputs/{lesson_id}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"PDF Upload කරමින් පවතී: {file_name}...")
    
    try:
        uploaded_file = client.files.upload(file=pdf_path)
        
        # ඔබගේ සම්පූර්ණ Master Prompt එක මෙතනින් AI එකේ මොළයට කාවද්දයි
        chat = client.chats.create(model=MODEL_ID, config={'system_instruction': FULL_MASTER_PROMPT})
        
        lesson_data = {"parts": {}}

        print("මාතෘකා 10 වෙන් කරගනිමින්...")
        # PDF එක ලබා දී එය මාතෘකා 10කට කඩන්න යැයි පවසයි
        init_res = chat.send_message(f"මෙම PDF ගොනුව {uploaded_file.uri} කියවා, එය ඉගැන්වීම සඳහා තාර්කික කොටස් 10කට කඩා, ඒ මාතෘකා 10 පමණක් ලැයිස්තුවක් ලෙස දෙන්න.")
        
        # කොටස් 10 ක් සඳහා පිළිවෙලින් විධාන නිකුත් කිරීම
        for i in range(1, 11):
            print(f"--- කොටස {i} සකසමින් පවතී (High Quality Generation) ---")
            
            # 1. Smart Note (විධානය යැවීම)
            print(f"Generating {i} smart note...")
            note_res = chat.send_message(f"විධානය: {i} smart note")
            
            # 2. Video Script (විධානය යැවීම - අඛණ්ඩ මතකය සහිතව)
            print(f"Generating {i} script...")
            script_res = chat.send_message(f"විධානය: {i} script")
            
            # 3. HTML Slides (විධානය යැවීම)
            print(f"Generating {i} html slides...")
            html_res = chat.send_message(f"විධානය: {i} html slides")
            
            part_content = {
                "smart_note": note_res.text,
                "video_script": script_res.text,
                "html_slides": html_res.text
            }
            lesson_data["parts"][f"part_{i}"] = part_content
            
            # Artifacts සඳහා සේව් කිරීම (HTML සහ Text)
            with open(f"{output_dir}/part_{i}_slides.html", "w", encoding="utf-8") as f:
                f.write(html_res.text.replace("```html", "").replace("```", ""))
            with open(f"{output_dir}/part_{i}_content.txt", "w", encoding="utf-8") as f:
                f.write(f"--- SMART NOTE ---\n{note_res.text}\n\n--- VIDEO SCRIPT ---\n{script_res.text}")
                
            time.sleep(15) # Google API limit එකට අහු නොවී ඉහළ Quality එකක් ලබා ගැනීමට විරාමයක්

        # 4. MCQ JSON (අවසාන විධානය)
        print("Generating MCQ JSON files (120 Questions)...")
        mcq_res = chat.send_message("විධානය: 4 JSON files")
        
        try:
            json_str = mcq_res.text.strip().replace("```json", "").replace("```", "")
            quiz_data = json.loads(json_str)
            lesson_data["quizzes"] = quiz_data
            with open(f"{output_dir}/quizzes.json", "w", encoding="utf-8") as f:
                json.dump(quiz_data, f, indent=4, ensure_ascii=False)
        except:
            print("JSON සෑදීමේ දෝෂයකි. Raw text ලෙස සේව් කෙරේ.")
            with open(f"{output_dir}/quizzes_raw.txt", "w", encoding="utf-8") as f:
                f.write(mcq_res.text)

        # Firebase Update
        db.reference(f'lessons/{lesson_id}').set(lesson_data)
        print(f"--- සාර්ථකව නිම කරන ලදී: {lesson_id} ---")

    except Exception as e:
        print(f"දෝෂයක් සිදුවිය: {e}")

def main():
    input_folder = "inputs"
    os.makedirs("outputs", exist_ok=True)
    if not os.path.exists(input_folder): return
    files =[f for f in os.listdir(input_folder) if f.endswith(".pdf")]
    for file_name in files:
        process_lesson(os.path.join(input_folder, file_name), file_name)

if __name__ == "__main__":
    main()
