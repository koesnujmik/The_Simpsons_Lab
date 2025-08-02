# The_Simpsons_Lab.
Prompetheus 2025-1 Project

<div align="center">
<img width="416" height="232" alt="image" src="https://github.com/user-attachments/assets/1a8749c8-c3af-4c05-965f-68fe82dc9a8d" />
</div>

## Overview

**The Simpsons Lab** is not just an automated video editing tool —  
it is an experimental research project that attempts to **quantify and structure human laughter** through AI.

Using *The Simpsons*, a globally acclaimed comedy animation series, as our dataset,  
we have developed an AI-driven pipeline that can:

- Detect humorous scenes  
- Plan edits based on narration, subtitle timing, and contextual cues  
- Automatically generate full short-form videos, including subtitles and narration

This project is not merely about summarizing funny content.  
It explores a deeper question:

> **Can AI edit content in a way that actually makes people laugh?**

We believe this is the world’s **first research project on AI-powered humor editing** —  
a bold attempt at the intersection of media automation, affective computing, and narrative intelligence.





## Pipeline

The Simpsons Lab operates through a 3-stage pipeline powered by LLM-based scene understanding and automated video editing.

---

### Step 1 – Scene Analysis & Highlight Selection

**Goal**  
Automatically identify the funniest clips across an entire Simpsons episode and generate metadata describing each clip.

**Process**

- **Full Video Segmentation**:  
  The Gemini Agent (LLM1) analyzes the full episode by splitting it into 2-minute segments.

- **Humor Scoring**:  
  Each segment is evaluated using a prompt that includes predefined humor cues (e.g., screams, ad-libs, explosions), scoring each on a 1–10 scale.

- **Top 5 Clip Selection & Summarization**:  
  The five clips with the highest humor scores are selected. Each is automatically described in natural language.

**Output**  
A JSON file containing:

[
  {
    "start_time": 162,
    "end_time": 174,
    "score": 9.2,
    "description": "Homer sets off a fire alarm while panicking over a donut."
  },
]

### Our Team
<div align="center">
<img width="1084" height="615" alt="image" src="https://github.com/user-attachments/assets/72dd91a6-9c3e-4579-81f4-22b0bc279179" />
</div>



**Welcome to The Simpsons Lab.**
_— Director, Junseok Kim, Wonjun Lee, Youngwoong Kim, Soobin Hwang_

