# 🖼️ Screen Capture + Gemini AI Analyzer

A simple but powerful Python tool that lets you **select any area on your screen**, capture it instantly, and send it to **Google Gemini** along with your custom prompt for real-time AI analysis.

This tool is built for anyone who wants fast, on-demand screenshot understanding — OCR, UI debugging, object detection, code extraction, visual explanations, and more.

---

## ⚙️ How It Works

When you run the program:

1. A **translucent overlay** appears on your screen.
2. Your cursor changes to a **crosshair** for precision.
3. You **click and drag** to select the area you want to capture.
4. The selected image is immediately sent to **Gemini AI** with your prompt.
5. The AI's response is returned instantly.

No clutter. No extra steps. Just *select → analyze → done*.

---

## ⚠️ Required Setup (Do This Before Running)

### 🔑 1. Add Your Gemini API Key  
Open the main file and replace the placeholder:

```python
genai.configure(api_key="YOUR_API_KEY_HERE")
