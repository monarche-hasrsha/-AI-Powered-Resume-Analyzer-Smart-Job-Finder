# AI Resume Job Finder MVP - Using Official SerpAPI Google Jobs API
# ---------------------------------------------------------------
# Updated: Proper SerpAPI Google Jobs API implementation with correct parameters
# ---------------------------------------------------------------

import streamlit as st
import hashlib
import functools
import datetime
import pdfplumber  # Using pdfplumber instead of PyMuPDF
import ollama
import httpx
import feedparser
import os
from serpapi.google_search import GoogleSearch
from jobs.search_api import fetch_google_jobs_serpapi, enhanced_jobicy_search
# CRITICAL: set_page_config MUST be the very first Streamlit command
st.set_page_config(page_title="AI Resume Analyzer + Job Finder", layout="wide")

# ────────────────────────────────────────────────  CONFIG  ──────────────────────────────────────────────
def get_serpapi_key():
    """Get SERPAPI key from environment or Streamlit secrets"""
    try:
        return st.secrets.get("SERPAPI_KEY", os.getenv("SERPAPI_KEY"))
    except Exception:
        return os.getenv("SERPAPI_KEY")

# ──────────────────── PDF ➞ TEXT (sanitised) ────────────────────
def extract_text_from_pdf(upload, max_chars=60_000) -> str:
    """Extract text from uploaded PDF file with sanitization."""
    try:
        with pdfplumber.open(upload) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                if len(text) >= max_chars:
                    break
            text = text[:max_chars]
            return "".join(ch for ch in text if 31 < ord(ch) < 127 or ch in "\n\r\t")
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""

# ──────────────────── CACHED OLLAMA CALLS ────────────────────
@functools.lru_cache(maxsize=128)
def _ollama(model: str, key: str, prompt: str) -> str:
    """Cached Ollama chat completion call."""
    try:
        response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]
    except Exception as e:
        print(f"Ollama error: {e}")
        return ""

def ask_ollama(model: str, prompt: str, resume_hash: str) -> str:
    """Ask Ollama with caching based on resume hash."""
    try:
        return _ollama(model, resume_hash + prompt[:40], prompt)
    except Exception as e:
        print(f"Ollama not available: {e}")
        return ""

# ──────────────────── AI-POWERED JOB ROLE DETECTION ────────────────────
def detect_suitable_job_roles(resume_text: str, resume_hash: str) -> dict:
    """Use Ollama AI to intelligently detect suitable job roles for the user."""
    
    role_detection_prompt = f"""
    Analyze this resume and determine the most suitable job roles for this person. Consider their:
    - Skills and technologies mentioned
    - Work experience and career progression
    - Education and certifications
    - Projects and achievements
    - Industry experience

    Based on the resume content, provide:
    1. PRIMARY ROLE: The single best-fitting job title they should target
    2. ALTERNATIVE ROLES: 3-4 other suitable job titles they could apply for
    3. CAREER LEVEL: Entry/Mid/Senior level assessment
    4. KEY STRENGTHS: Top 3 skills/areas that make them suitable
    5. RECOMMENDED KEYWORDS: Best search terms for job hunting

    Format your response as:
    PRIMARY ROLE: [job title]
    ALTERNATIVE ROLES: [role1], [role2], [role3], [role4]
    CAREER LEVEL: [level]
    KEY STRENGTHS: [strength1], [strength2], [strength3]
    RECOMMENDED KEYWORDS: [keyword1], [keyword2], [keyword3]

    Resume content:
    {resume_text}
    """
    
    response = ask_ollama("mistral", role_detection_prompt, resume_hash)
    
    # Parse the structured response
    parsed_roles = {
        "primary_role": "Software Engineer",
        "alternative_roles": ["Developer", "Programmer", "Engineer"],
        "career_level": "Mid Level",
        "key_strengths": ["Programming", "Problem Solving", "Technology"],
        "recommended_keywords": ["software engineer", "developer", "programming"]
    }
    
    if response:
        lines = response.split('\n')
        for line in lines:
            if line.startswith('PRIMARY ROLE:'):
                parsed_roles["primary_role"] = line.replace('PRIMARY ROLE:', '').strip()
            elif line.startswith('ALTERNATIVE ROLES:'):
                alt_roles = line.replace('ALTERNATIVE ROLES:', '').strip()
                parsed_roles["alternative_roles"] = [role.strip() for role in alt_roles.split(',')]
            elif line.startswith('CAREER LEVEL:'):
                parsed_roles["career_level"] = line.replace('CAREER LEVEL:', '').strip()
            elif line.startswith('KEY STRENGTHS:'):
                strengths = line.replace('KEY STRENGTHS:', '').strip()
                parsed_roles["key_strengths"] = [strength.strip() for strength in strengths.split(',')]
            elif line.startswith('RECOMMENDED KEYWORDS:'):
                keywords = line.replace('RECOMMENDED KEYWORDS:', '').strip()
                parsed_roles["recommended_keywords"] = [keyword.strip() for keyword in keywords.split(',')]
    
    return parsed_roles

# ──────────── PROPER SERPAPI GOOGLE JOBS IMPLEMENTATION ────────────
def fetch_google_jobs_serpapi(detected_roles: dict, location: str = "Remote", limit: int = 15):
    """Fetch jobs using proper SerpAPI Google Jobs API implementation."""
    api_key = get_serpapi_key()
    if not api_key:
        print("SERPAPI_KEY not set. Skipping Google Jobs search.")
        return []
    
    all_jobs = []
    
    # Create search queries based on AI recommendations
    search_queries = [
        detected_roles["primary_role"],
        f"{detected_roles['primary_role']} {detected_roles['career_level'].lower()}",
    ]
    
    # Add alternative roles and keywords
    search_queries.extend(detected_roles["alternative_roles"][:2])
    search_queries.extend(detected_roles["recommended_keywords"][:2])
    
    for query in search_queries:
        if len(all_jobs) >= limit:
            break
            
        # Proper SerpAPI Google Jobs parameters based on documentation[1][2]
        params = {
            "engine": "google_jobs",           # Required: Set to google_jobs
            "q": f"{query} remote",            # Search query
            "location": location,              # Geographic location
            "hl": "en",                       # Language (English)
            "gl": "us",                       # Country (US)
            "api_key": api_key,               # Your SerpAPI key
            "no_cache": False                 # Allow cached results for faster response
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Check for errors in response
            if 'error' in results:
                print(f"SerpAPI Error: {results['error']}")
                continue
            
            jobs_results = results.get("jobs_results", [])
            
            for job in jobs_results:
                if len(all_jobs) >= limit:
                    break
                
                # Extract job data according to SerpAPI response structure[6]
                job_data = {
                    "title": job.get("title"),
                    "company": job.get("company_name"),
                    "location": job.get("location"),
                    "link": job.get("related_links", [{}])[0].get("link") if job.get("related_links") else None,
                    "posted": job.get("detected_extensions", {}).get("posted_at"),
                    "schedule_type": job.get("detected_extensions", {}).get("schedule_type"),
                    "via": job.get("via"),
                    "job_id": job.get("job_id"),
                    "thumbnail": job.get("thumbnail"),
                    "description": job.get("description"),
                    "match_reason": f"Matches: {query}"
                }
                
                # Avoid duplicates
                if not any(existing_job["title"] == job_data["title"] and 
                         existing_job["company"] == job_data["company"] 
                         for existing_job in all_jobs):
                    all_jobs.append(job_data)
            
        except Exception as e:
            print(f"Google Jobs fetch failed for query '{query}': {e}")
            continue
    
    return all_jobs

# ──────────── FALLBACK SOURCES WITH AI KEYWORDS ────────────
def enhanced_jobicy_search(detected_roles: dict, limit: int = 10):
    """Search Jobicy using AI-detected keywords."""
    try:
        data = httpx.get("https://jobs.jobicy.com/api/v2/remote-jobs", timeout=15).json().get("jobs", [])
        cutoff = datetime.date.today() - datetime.timedelta(days=30)
        
        # Use AI-recommended keywords for better matching
        search_terms = [detected_roles["primary_role"]] + detected_roles["recommended_keywords"]
        
        matched_jobs = []
        for job in data:
            job_date = datetime.date.fromisoformat(job["published_at"][:10])
            if job_date >= cutoff:
                for term in search_terms:
                    if term.lower() in job["title"].lower() or term.lower() in job.get("description", "").lower():
                        matched_jobs.append({
                            "url": job["url"],
                            "title": job["title"],
                            "company": job.get("company_name", "Unknown"),
                            "match_reason": f"Matches: {term}"
                        })
                        break
        
        return matched_jobs[:limit]
    except Exception as e:
        print(f"Jobicy API error: {e}")
        return []

# ──────────────────── MAIN STREAMLIT APP ────────────────────
st.title("🤖 AI-Powered Resume Analyzer + Smart Job Finder")
st.caption("Upload your résumé and let AI intelligently detect the best job roles for you!")

def _display_jobs(jobs: list[dict]):
    """Render job list in a clean markdown table."""
    if not jobs:
        st.write("_No jobs to display._")
        return
    cols = ["Title", "Company", "Location", "Posted", "Type", "Match Reason", "Link"]
    header = "| " + " | ".join(cols) + " |"
    divider = "|" + "|".join(["---"] * len(cols)) + "|"
    rows = []
    for j in jobs:
        title = j.get("title", "")
        company = j.get("company", "Remote")
        loc = j.get("location", "")
        posted = j.get("posted", "") or "-"
        typ = j.get("schedule_type", "") or "-"
        reason = j.get("match_reason", "")
        link = j.get("link") or j.get("url")
        link_md = f"[Apply]({link})" if link else ""
        rows.append(f"| {title} | {company} | {loc} | {posted} | {typ} | {reason} | {link_md} |")
    st.markdown("\n".join([header, divider] + rows), unsafe_allow_html=True)

uploaded_file = st.file_uploader("📄 Upload your résumé (PDF only)", type=["pdf"])

if uploaded_file:
    with st.spinner("🧠 AI is analyzing your résumé..."):
        resume_text = extract_text_from_pdf(uploaded_file)
        if not resume_text:
            st.error("Could not extract text from PDF. Please try a different file.")
            st.stop()

        rhash = hashlib.sha256(resume_text.encode()).hexdigest()
        
        # Generate summary
        summary_prompt = f"Provide a concise professional summary of this résumé, highlighting key qualifications and experience:\n\n{resume_text}"
        summary = ask_ollama("mistral", summary_prompt, rhash)
        
        # AI-powered role detection
        detected_roles = detect_suitable_job_roles(resume_text, rhash)
        
        if not summary:
            st.warning("Ollama not available. Using default analysis.")
            summary = "AI analysis not available. Please install Ollama for enhanced resume analysis."

    # Display AI Analysis Results
    st.subheader("📄 Professional Summary")
    st.markdown(summary)
    
    st.subheader("🎯 AI-Detected Suitable Job Roles")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"**🏆 Primary Recommended Role:** {detected_roles['primary_role']}")
        st.markdown(f"**📊 Career Level:** {detected_roles['career_level']}")
        
        st.markdown("**🔄 Alternative Suitable Roles:**")
        for i, role in enumerate(detected_roles['alternative_roles'], 1):
            st.markdown(f"{i}. {role}")
    
    with col2:
        st.markdown("**💪 Key Strengths:**")
        for strength in detected_roles['key_strengths']:
            st.markdown(f"• {strength}")
    
    # Job Search Section
    st.subheader("🤝 Smart Job Search")
    st.markdown(f"**Searching for roles matching:** {detected_roles['primary_role']} and related positions")
    
    # Location selection
    location_options = ["United States", "Worldwide", "New York, NY", "San Francisco, CA", "London, UK"]
    location = st.selectbox("🌍 Preferred Location", location_options, index=0)
    custom_location = st.text_input("Or enter custom location:", placeholder="e.g., Austin, TX")
    final_location = custom_location.strip() if custom_location.strip() else location
    if final_location.strip().lower() == "remote":
        final_location = ""

    if st.button("🔍 Find Perfect Job Matches", type="primary"):
        search_start_time = datetime.datetime.now()
        
        with st.spinner(f"🎯 AI is finding the best job matches using SerpAPI Google Jobs..."):
            # AI-optimized Google Jobs search using proper SerpAPI
            google_jobs = fetch_google_jobs_serpapi(detected_roles, final_location)
            
            if google_jobs:
                st.success(f"🎉 Found {len(google_jobs)} highly relevant job matches via SerpAPI!")
                with st.expander("🌐 Google Jobs - SerpAPI Results", expanded=True):
                    _display_jobs(google_jobs)
            
            # Enhanced fallback search
            with st.spinner("🔄 Searching additional sources..."):
                fallback_jobs = enhanced_jobicy_search(detected_roles)
                
                if fallback_jobs:
                    st.success(f"✨ Found {len(fallback_jobs)} additional opportunities!")
                    with st.expander("🌟 Additional Job Opportunities", expanded=True):
                        _display_jobs(fallback_jobs)
            
            # Search completion summary
            total_jobs = len(google_jobs) + len(fallback_jobs)
            search_time = (datetime.datetime.now() - search_start_time).total_seconds()
            
            if total_jobs == 0:
                st.warning("🤔 No matches found. This could mean:")
                st.info("""
                • Very specific/niche role - try broadening search terms
                • Limited opportunities in this field currently  
                • SerpAPI quota reached - check your account[1]
                • Try alternative roles from the AI recommendations above
                """)
            else:
                st.balloons()
                st.success(f"🎯 **Search Complete!** Found **{total_jobs} AI-matched jobs** in {search_time:.1f} seconds")
                
                # Show search insights
                st.info(f"""
                **🧠 AI Search Insights:**
                • Primary focus: {detected_roles['primary_role']} ({detected_roles['career_level']})
                • Alternative roles explored: {', '.join(detected_roles['alternative_roles'][:2])}
                • Key strengths highlighted: {', '.join(detected_roles['key_strengths'][:2])}
                • Powered by SerpAPI Google Jobs API[2]
                """)

else:
    st.info("👆 Upload your résumé to get AI-powered job role detection and smart job matching!")
    
    with st.expander("🚀 What's New - SerpAPI Google Jobs Integration"):
        st.markdown("""
        **🔧 Official SerpAPI Integration:**
        • Uses official Google Jobs API via SerpAPI[2]
        • Proper parameter structure following SerpAPI docs
        • Better error handling and response parsing
        • Access to comprehensive job data fields
        
        **🧠 AI-Powered Features:**
        • Ollama analyzes your entire resume context
        • Intelligent job role recommendations
        • Multi-query search strategy for better coverage
        • Explains why each job matches your profile
        """)
    
    with st.expander("⚙️ Setup Requirements"):
        st.markdown("""
        **Installation:**
        ```
        pip install streamlit pymupdf ollama httpx feedparser google-search-results
        ollama pull mistral
        ```
        
        **SerpAPI Configuration:**
        • Sign up at serpapi.com[1]
        • Get your API key from dashboard
        • Create `.streamlit/secrets.toml`
        • Add: `SERPAPI_KEY = "your_api_key_here"`
        
        **Run:** `streamlit run app.py`
        """)
