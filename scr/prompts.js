// src/prompts.js

const getSmartNotePrompt = (content) => `
📝 1. Master Prompt: Interactive Smart Note Generation (Sinhala)
(මෙතනට අර අපි කලින් හදාගත්ත පළමු Prompt එකේ සම්පූර්ණ විස්තරය Paste කරන්න...)
Input Data: ${content}
`;

const getVideoScriptPrompt = (content, smartNote) => `
🎬 2. Master Prompt: Video Script Generation (Sinhala for TTS)
(මෙතනට දෙවැනි Prompt එකේ සම්පූර්ණ විස්තරය Paste කරන්න...)
Input Data: PDF Content: ${content} | Smart Note: ${smartNote}
`;

const getHtmlSlidesPrompt = (content, smartNote, script) => `
💻 3. Master Prompt: Detailed HTML Slides Generation (Sinhala)
(මෙතනට තුන්වැනි Prompt එකේ සම්පූර්ණ විස්තරය Paste කරන්න...)
Input Data: PDF: ${content} | Note: ${smartNote} | Script: ${script}
`;

const getMcqPrompt = (content) => `
📊 4. Master Prompt: Assessment Generation (Sinhala)
(මෙතනට හතරවැනි Prompt එකේ සම්පූර්ණ විස්තරය Paste කරන්න...)
Input Data: ${content}
`;

module.exports = { getSmartNotePrompt, getVideoScriptPrompt, getHtmlSlidesPrompt, getMcqPrompt };
