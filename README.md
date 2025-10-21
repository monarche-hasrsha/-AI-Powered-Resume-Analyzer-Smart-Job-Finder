# AI-Powered Résumé Analyzer & Smart Job Finder



https://github.com/user-attachments/assets/152d9139-b882-4048-928a-f2b2b8e68110


A Streamlit application that leverages local LLMs (via **Ollama**) and the **SerpAPI Google Jobs** engine to:

1. Parse and summarise your résumé
2. Detect the most suitable job roles for your profile
3. Search Google Jobs and curated RSS feeds for matching opportunities
4. Display organised, de-duplicated job listings with handy apply links

---


An intelligent job matching application that analyzes your résumé using AI and recommends relevant job opportunities from various job boards.

## Features

- **Smart Résumé Parsing**: Extract structured information from PDF/DOCX résumés using local LLMs
- **Job Scraping**: Fetch job listings from Indeed RSS feeds
- **AI-Powered Matching**: Rank jobs based on semantic similarity to your skills
- **Interactive Web Interface**: Clean Streamlit UI for easy interaction
- **Local AI**: Uses Ollama for privacy-focused AI processing

## How It Works

1. **Upload**: Upload your résumé (PDF or DOCX format)
2. **Parse**: AI extracts your skills, experience, and education
3. **Search**: System fetches relevant job postings based on your skills
4. **Rank**: Jobs are ranked by relevance using embedding similarity
5. **Review**: Browse top matches with direct links to job postings

## Prerequisites

### 1. Install Ollama

Download and install Ollama from [https://ollama.ai](https://ollama.ai)

### 2. Install Required Ollama Models

```bash
# Install a chat model for résumé parsing
ollama pull mistral:latest

# Optional: Install an embedding model for better matching
ollama pull mistral-embed:latest
```

### 3. Python Requirements

Python 3.8+ is required.

## Installation

1. **Clone or download the project**
   ```bash
   cd job_matcher
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Ollama is running**
   ```bash
   ollama list
   ```
   You should see your installed models.

## Usage

1. **Start the application**
   ```bash
   streamlit run app.py
   ```

2. **Open your browser** to the URL shown (usually `http://localhost:8501`)

3. **Upload your résumé** (PDF or DOCX format)

4. **Enter location** (optional) for geographically relevant jobs

5. **Click "Find Jobs"** and wait for the AI to:
   - Parse your résumé
   - Fetch relevant job postings
   - Rank them by relevance

6. **Review results** and click through to job postings

## Project Structure

```
job_matcher/
├── app.py                # Streamlit web interface
├── resume_parser.py      # AI-powered résumé extraction
├── matcher.py            # Job ranking using embeddings
├── crawler/
│   └── indeed_rss.py    # Job scraping from Indeed RSS
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Configuration

### Ollama Models

- **Chat Model**: Used for résumé parsing (default: `mistral:latest`)
- **Embedding Model**: Used for job matching (default: `mistral-embed:latest`)
- **Fallback**: If Ollama models aren't available, uses SentenceTransformers

### Customization

You can modify:
- `max_jobs` in `crawler/indeed_rss.py` to fetch more/fewer jobs
- `top_k` in matching to show more/fewer results
- Embedding models in `matcher.py` for different matching algorithms

## Troubleshooting

### Common Issues

1. **"Error connecting to Ollama"**
   - Ensure Ollama is installed and running
   - Check that you have models installed: `ollama list`

2. **"No jobs retrieved"**
   - Try simpler skill keywords
   - Check your internet connection
   - Indeed may be rate-limiting requests

3. **"Could not extract skills from résumé"**
   - Ensure your résumé has clear text (not just images)
   - Try a different file format (PDF vs DOCX)
   - Check that the file isn't corrupted

4. **Slow performance**
   - Reduce `max_jobs` in the crawler
   - Use faster Ollama models
   - Consider using GPU acceleration for Ollama

### Performance Tips

- **GPU Acceleration**: If you have a compatible GPU, Ollama will automatically use it
- **Model Selection**: Smaller models (like `mistral:7b`) are faster than larger ones
- **Batch Processing**: The system processes jobs in batches for efficiency

## Privacy & Security

- **Local Processing**: All AI processing happens locally via Ollama
- **No Data Storage**: Résumés are processed in memory and not stored
- **Web Scraping**: Only public job postings are accessed

## Limitations

- **Job Sources**: Currently only supports Indeed RSS feeds
- **Rate Limiting**: Respectful delays between requests may slow job fetching
- **Accuracy**: AI parsing accuracy depends on résumé format and quality
- **Language**: Optimized for English résumés and job postings

## Future Enhancements

- Support for additional job boards (LinkedIn, Glassdoor, etc.)
- Advanced filtering (salary, company size, remote options)
- Résumé improvement suggestions
- Job application tracking
- Email notifications for new matches

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.
