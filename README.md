📸 Screen-Capture AI Analyzer

A lightweight Python tool that lets you select any area on your screen, capture it instantly, and analyze the image using Google Gemini based on your custom prompt.

Perfect for debugging UI, reading text from screenshots, quick OCR, visual explanation, or automating any image-analysis workflow.

🚀 How It Works

When you run the program, three things happen:

A translucent overlay covers your screen.

Your cursor becomes a crosshair — this means you're in selection mode.

You drag with your mouse to capture the area you want analyzed.

Once you release the mouse, the tool instantly sends the captured region to Gemini along with your chosen prompt and returns the AI's response.

No fluff. No extra steps. Just select → analyze → done.

⚠️ Before You Run It — DO NOT IGNORE THIS

You must change these three things or the program will not work correctly:

✅ 1. Add your Gemini API key

Open the main file and replace the placeholder with your own key:

genai.configure(api_key="YOUR_API_KEY_HERE")

✅ 2. Write your custom prompt

Go to line 64 (or wherever your prompt variable is) and modify it to tell Gemini what to do with the image.

Example:

prompt = "Extract all text from this screenshot and summarize it clearly."

✅ 3. Keep all project files inside the same folder

The script depends on local imports. If the structure breaks, your program will break.

🎯 Features

✔️ Interactive screen region selector

✔️ Transparent overlay for precision

✔️ Crosshair cursor for accurate dragging

✔️ Instant screenshot capture

✔️ Gemini 1.5-powered image analysis

✔️ Fully customizable prompt

✔️ Works on Windows (recommended)

✔️ Lightweight and dependency-friendly

🛠️ Requirements

Python 3.8+

Google Gemini Python SDK

PyQt5 (or whatever GUI module you're using)

Pillow

Any other modules your script imports

Install with:

pip install -r requirements.txt

▶️ Usage

Run the script:

python main.py


Then:

Wait for the screen overlay to appear

Click + drag to select the region

Release the mouse

Get instant AI analysis in the console/output window

📌 Example Use-Cases

OCR a selected area

Explain UI elements

Analyze graphs or charts

Extract code from screenshots

Debug visual errors

Recognize objects or text instantly
