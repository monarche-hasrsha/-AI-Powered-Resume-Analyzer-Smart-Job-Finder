# AI-Powered Résumé Analyzer & Smart Job Finder

A privacy-focused Streamlit application that uses **local LLMs (via [Ollama](https://ollama.ai))** and the **official SerpAPI Google Jobs API** to analyse your résumé and surface the most relevant job openings.

---

## ✨ Key Features

• **Résumé Text Extraction (PDF)** – fast, offline extraction via PyMuPDF  
• **AI Role Detection** – Ollama (Mistral) identifies primary & alternative job roles, key strengths, and keywords  
• **Google Jobs Search** – queries the SerpAPI Google Jobs engine with AI-optimised keywords  
• **Fallback Feeds** – scans curated remote-job RSS feeds (We Work Remotely, Himalayas)  
• **Clean Streamlit UI** – instant feedback, spinners, markdown tables, duplicate filtering  
• **100 % Local AI** – résumé never leaves your machine; only public job boards are accessed

---

## 🚀 Quick Start

```bash
# 1. Clone
 git clone https://github.com/<your-org>/job_matcher.git
 cd job_matcher

# 2. Install Python deps
 pip install -r requirements.txt

# 3. Install & start Ollama, then pull the model used by the app
 curl -fsSL https://ollama.ai/install.sh | sh   # or follow the docs for your OS
 ollama pull mistral

# 4. Add your SerpAPI key (free trial available)
 echo "SERPAPI_KEY=YOUR_KEY_HERE" > .streamlit/secrets.toml  # or set env-var

# 5. Run the app
 streamlit run app.py
```

Open the URL shown in the terminal (default: `http://localhost:8501`).

---

## 🗂️ Project Structure

```text
job_matcher/
├── app.py               # Streamlit web interface & orchestration
├── jobs/
│   └── search_api.py    # SerpAPI & RSS-feed fetch helpers
├── requirements.txt
└── README.md
```

---

## ⚙️ Configuration Details

| Item | Where | Default |
|------|-------|---------|
| **SerpAPI key** | `.streamlit/secrets.toml` `SERPAPI_KEY` or env-var | – |
| **Ollama model** | hard-coded in `app.py` (`mistral`) | `mistral` |
| **RSS feeds** | `_RSS_FEEDS` list in `jobs/search_api.py` | We Work Remotely & Himalayas |
| **Job limit** | `limit` arg in `fetch_google_jobs_serpapi()` / `enhanced_jobicy_search()` | 15 / 10 |

Tweak these to suit your needs.

---

## 🙋‍♂️ Usage Tips

1. Upload a PDF résumé (text-based, not scanned images).  
2. Wait for the AI analysis & role detection (few seconds).  
3. Pick a location or leave as *Remote* for worldwide search.  
4. Click **Find Perfect Job Matches**.  
5. Browse the results – duplicates filtered, newest first – and click *Apply* links.

---

## 🛠️ Troubleshooting

| Issue | Fix |
|-------|-----|
| *“SERPAPI_KEY not set”* | Add the key to secrets or export as env-var |
| *Ollama not running* | `ollama serve` or restart the desktop app |
| *No jobs returned* | Broaden keywords / location or check API quota |
| *PDF text empty* | Ensure résumé is text-based, not just images |

---

## 🤝 Contributing

Pull requests, feature ideas, and bug reports are welcome!

---

## © License

Licensed under the MIT License.
