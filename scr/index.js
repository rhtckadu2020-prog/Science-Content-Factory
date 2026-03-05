// src/index.js
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { GoogleGenerativeAI } = require("@google/generative-ai");
const { getSmartNotePrompt, getVideoScriptPrompt, getHtmlSlidesPrompt, getMcqPrompt } = require('./prompts');

// Configuration
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
// Note: අපි කතා කරපු "Flash Lite" මොඩලය ආවම මෙතන නම වෙනස් කරන්න.
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" }); 

async function generateContent() {
    try {
        console.log("🚀 Starting E-Learning Content Generation...");

        // 1. Read Input File
        const inputPath = path.join(__dirname, '../input/lesson.txt');
        if (!fs.existsSync(inputPath)) throw new Error("Input file not found!");
        const content = fs.readFileSync(inputPath, 'utf-8');
        console.log("✅ Input file read successfully.");

        // Ensure output directory exists
        const outputDir = path.join(__dirname, '../output');
        if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir);

        // --- STEP 1: Smart Note ---
        console.log("⏳ Generating Smart Note...");
        const result1 = await model.generateContent(getSmartNotePrompt(content));
        const smartNote = result1.response.text();
        fs.writeFileSync(path.join(outputDir, '1_SmartNote.txt'), smartNote);
        console.log("✅ Smart Note Saved.");

        // --- STEP 2: Video Script ---
        console.log("⏳ Generating Video Script...");
        const result2 = await model.generateContent(getVideoScriptPrompt(content, smartNote));
        const videoScript = result2.response.text();
        fs.writeFileSync(path.join(outputDir, '2_VideoScript.txt'), videoScript);
        console.log("✅ Video Script Saved.");

        // --- STEP 3: HTML Slides ---
        console.log("⏳ Generating HTML Slides...");
        const result3 = await model.generateContent(getHtmlSlidesPrompt(content, smartNote, videoScript));
        const htmlSlides = result3.response.text();
        // Extract HTML only if wrapped in backticks
        const cleanHtml = htmlSlides.replace(/```html|```/g, '');
        fs.writeFileSync(path.join(outputDir, '3_Slides.html'), cleanHtml);
        console.log("✅ HTML Slides Saved.");

        // --- STEP 4: MCQ JSON ---
        console.log("⏳ Generating MCQs...");
        const result4 = await model.generateContent(getMcqPrompt(content));
        const mcqJson = result4.response.text();
        // Extract JSON only
        const cleanJson = mcqJson.replace(/```json|```/g, '');
        fs.writeFileSync(path.join(outputDir, '4_Assessment.json'), cleanJson);
        console.log("✅ MCQs Saved.");

        console.log("🎉 All tasks completed successfully! Check the 'output' folder.");

    } catch (error) {
        console.error("❌ Error:", error);
        process.exit(1);
    }
}

generateContent();
