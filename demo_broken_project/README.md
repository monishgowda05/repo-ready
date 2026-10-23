# My Cool AI Hackathon App
Built with AI. Everything is 100% MIT licensed!
---

## 🧠 Open-Weight AI Model & Licensing Attribution

> **Notice on Open-Weight vs. Open-Source Terms:**  
> The source code in this repository is licensed under the **MIT License** (see `LICENSE`).  
> In accordance with Hacktoberfest and Responsible AI open standards, the open-weight machine learning models 
> utilized herein are subject to their respective creators' model licenses and acceptable use policies.

| Model Name | Category | Provider / Terms | Official License URL |
| :--- | :--- | :--- | :--- |
| **Google Gemma 2** | Open-Weight SLM | Provider Terms | [Terms of Use](https://ai.google.dev/gemma/terms) |
| **Meta Llama 3** | Open-Weight LLM | Provider Terms | [Terms of Use](https://llama.meta.com/llama3/license/) |

## ⚡ Quickstart & Reproducibility (Judge Guide)

### 1. Prerequisites
- Python 3.10+ installed
- [Ollama](https://ollama.com) installed and running locally

### 2. Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd <repository-directory>

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Pull the required open-weight model
ollama pull gemma2:2b
```

### 3. Running the Application
```bash
python main.py
```

