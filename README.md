🚀 LLM Router Service
A unified API gateway for multiple Large Language Model (LLM) providers including OpenAI, Google Gemini, and Groq. Route requests intelligently, manage API keys securely, and get consistent responses across different LLM providers.

🚀 Quick Start
1. Clone the Repository
bashgit clone https://github.com/yourusername/llm-router.git
cd llm-router
2. Environment Setup
bash# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
3. Install Dependencies
bash# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install packages
pip install -r requirements.txt