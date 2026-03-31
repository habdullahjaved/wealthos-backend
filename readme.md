# ⚙️ WealthOS Backend — FastAPI + pandas + Groq AI

> Python backend powering the WealthOS finance dashboard. Provides pandas-based transaction analytics and a streaming Groq Llama 3.3 AI finance assistant via Server-Sent Events.

**🌐 API Base URL:** [https://wealthos-api-production-47bf.up.railway.app](https://wealthos-api-production-47bf.up.railway.app)  
**🖥 Frontend Repo:** [wealthos-frontend](https://github.com/YOUR_USERNAME/wealthos-frontend)  
**📊 Frontend Demo:** [https://wealthosf.vercel.app](https://wealthosf.vercel.app)

---

## 📸 What This Does

### `POST /insights` — pandas Transaction Analytics

- Accepts a `user_id` and `months` range
- Fetches transactions directly from **Supabase** using the service role key (bypasses RLS)
- Runs **pandas** aggregations to compute:
  - Monthly income vs expenses vs net cashflow
  - Spending breakdown by category with percentages and colour codes
  - Top 5 merchants by total spend
  - Average daily spend, total income, total expenses, savings rate
- Returns structured JSON consumed by Recharts in the frontend

### `POST /chat` — Groq Llama 3.3 Streaming Assistant

- Accepts a conversation history + financial context object from Next.js
- Builds a dynamic system prompt injecting the user's real transaction data
- Streams tokens from **Groq API (Llama 3.3 70B)** as **Server-Sent Events**
- Uses `AsyncGroq` — fully non-blocking, no event loop stalls
- Frontend receives and renders tokens in real time

---

## 🛠 Tech Stack

| Layer           | Technology                     |
| --------------- | ------------------------------ |
| Framework       | FastAPI                        |
| Language        | Python 3.12                    |
| Data Processing | pandas + numpy                 |
| AI / LLM        | Groq API (Llama 3.3 70B)       |
| Database Client | supabase-py                    |
| Streaming       | AsyncGroq + Server-Sent Events |
| Validation      | Pydantic v2                    |
| Server          | Uvicorn                        |
| Hosting         | Railway (free tier)            |

---

## 📁 Project Structure

```
wealthos-backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan, router registration
│   └── routers/
│       ├── chat.py          # POST /chat — Groq SSE streaming
│       └── insights.py      # POST /insights — pandas analytics
├── Procfile                 # Railway start command
├── runtime.txt              # Python 3.12.0
├── requirements.txt         # Pinned dependencies
└── .env                     # Local env vars (never committed)
```

---

## 🚀 Getting Started Locally

### Prerequisites

- Python 3.12
- A [Supabase](https://supabase.com) project with a `transactions` table
- A [Groq](https://console.groq.com) API key (free tier)

### 1. Clone and create virtual environment

```bash
git clone https://github.com/habdullahjaved/wealthos-backend
cd wealthos-backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Create `.env` in the project root:

```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJxxx   # service_role key, not anon key
ALLOWED_ORIGINS=http://localhost:3000
ENVIRONMENT=development
```

> ⚠️ Use the **service_role** key from Supabase → Project Settings → API. This bypasses RLS so the backend can read any user's transactions securely server-side.

### 4. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Test the chat endpoint

```bash
python test_chat.py
```

Expected output:

```
Hello! I'm WealthOS AI. How can I help with your finances today?
✅ Stream complete
```

---

## 🔌 API Reference

### `GET /health`

Health check endpoint. Used by Railway and frontend warm-up pings.

```json
{ "status": "ok", "service": "wealthos-api" }
```

---

### `POST /insights`

**Request:**

```json
{
  "user_id": "uuid-of-user",
  "months": 3
}
```

**Response:**

```json
{
  "monthly_totals": [
    { "month": "Jan 2025", "income": 5000, "expenses": 3200, "net": 1800 }
  ],
  "category_breakdown": [
    {
      "category": "Food & Dining",
      "amount": 850.0,
      "percentage": 26.5,
      "color": "#34d399"
    }
  ],
  "top_merchants": [{ "merchant": "Carrefour", "total": 420.0, "count": 8 }],
  "avg_daily_spend": 106.67,
  "total_income": 5000.0,
  "total_expenses": 3200.0,
  "savings_rate": 36.0
}
```

---

### `POST /chat`

**Request:**

```json
{
  "messages": [
    { "role": "user", "content": "Where did I spend the most this month?" }
  ],
  "context": {
    "recent_transactions": [...],
    "categories": [{ "category": "Food & Dining", "amount": 850 }],
    "monthly_summary": { "Food & Dining": 850, "Transport": 320 }
  }
}
```

**Response:** Server-Sent Events stream

```
data: {"content": "Based"}
data: {"content": " on"}
data: {"content": " your data..."}
data: [DONE]
```

---

## 🧠 Streaming Architecture

```
Next.js Route Handler
  └── POST /chat with messages + Supabase context
        └── FastAPI builds system prompt with financial data
              └── AsyncGroq.chat.completions.create(stream=True)
                    └── async for chunk → yield SSE data frame
                          └── StreamingResponse pipes to Next.js
                                └── Next.js pipes to browser
                                      └── Hook reads ReadableStream token by token
```

Key implementation details:

- Uses `AsyncGroq` (not sync `Groq`) to avoid blocking FastAPI's event loop
- `stream=True` on `completions.create()` — compatible with groq `1.1.2`
- `X-Accel-Buffering: no` header prevents Nginx/Railway proxy buffering
- Financial context is injected into the system prompt by Next.js — backend never touches auth

---

## 📦 Dependencies

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
python-dotenv==1.0.1
pandas==2.2.2
numpy==1.26.4
groq==1.1.2
supabase==2.15.0
httpx==0.27.2
pydantic==2.8.2
```

> Versions are pinned for Railway compatibility with Python 3.12. `numpy==1.26.4` and `pandas==2.2.2` use pre-built wheels — no Rust/C compilation on deploy.

---

## 🌍 Deployment (Railway)

1. Push to GitHub
2. New Project → Deploy from GitHub repo
3. Add environment variables in Railway → Variables tab:

```
GROQ_API_KEY
SUPABASE_URL
SUPABASE_SERVICE_KEY
ALLOWED_ORIGINS=https://wealthosf.vercel.app,http://localhost:3000
ENVIRONMENT=production
PYTHON_VERSION=3.12.0
```

4. Settings → Networking → Generate Domain

Railway uses the `Procfile` to start the server:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## ⚠️ Notes

- **No cold starts** — Railway keeps the service always on (unlike Render free tier)
- **CORS** — configured via `ALLOWED_ORIGINS` env var, comma-separated
- **Swagger UI** — available at `/docs` when `ENVIRONMENT=development`
- **Service role key** — never expose this to the frontend; backend only

---

## 📄 License

MIT
