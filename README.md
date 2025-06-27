LLM Router
A unified API gateway for multiple LLM providers (OpenAI, Gemini, Groq).
Setup

Clone and install
bashgit clone <repo-url>
cd llm-router
pip install -r requirements.txt

Configure environment
bashcp .env.example .env
# Edit .env with your API keys

Start server
bashuvicorn src.llm_router.main:app --reload

Access API docs
http://localhost:8000/docs
