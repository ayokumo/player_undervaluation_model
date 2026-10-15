"""Small web service around the RAG scouting assistant.

GET  /          one page demo with a question box
POST /ask       {"question": "..."} returns answer, sources, route
GET  /health    checks the database and reports index size

A public demo spends real API credit, so there are three guards, all set by env vars:
  MAX_QUESTION_CHARS   longest accepted question (default 300)
  DAILY_LIMIT_PER_IP   questions per IP per day (default 15)
  DAILY_LIMIT_TOTAL    questions for the whole service per day (default 200)
Counters live in memory, so they reset when the container restarts.
"""
import os
import threading
from datetime import date

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Football scouting assistant", docs_url=None, redoc_url=None)

MAX_CHARS = int(os.environ.get("MAX_QUESTION_CHARS", "300"))
PER_IP = int(os.environ.get("DAILY_LIMIT_PER_IP", "15"))
TOTAL = int(os.environ.get("DAILY_LIMIT_TOTAL", "200"))

_lock = threading.Lock()
_counts: dict = {"day": date.today(), "total": 0, "ip": {}}


def _answer(question: str) -> dict:
    # imported here so the service starts (and /health works) even before the model loads
    from rag.chain import answer
    return answer(question)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _charge(ip: str) -> None:
    with _lock:
        if _counts["day"] != date.today():
            _counts.update(day=date.today(), total=0, ip={})
        if _counts["total"] >= TOTAL:
            raise HTTPException(429, "The demo has reached its daily limit. Please try again tomorrow.")
        if _counts["ip"].get(ip, 0) >= PER_IP:
            raise HTTPException(429, f"Limit of {PER_IP} questions per day reached for this address.")
        _counts["total"] += 1
        _counts["ip"][ip] = _counts["ip"].get(ip, 0) + 1


class Question(BaseModel):
    question: str


@app.get("/health")
def health() -> dict:
    from rag.store import connect
    with connect() as c:
        n = c.execute("SELECT count(*) AS n FROM rag.documents").fetchone()["n"]
    return {"status": "ok", "documents": n}


@app.post("/ask")
def ask(body: Question, request: Request) -> dict:
    q = body.question.strip()
    if not q:
        raise HTTPException(400, "Ask a question.")
    if len(q) > MAX_CHARS:
        raise HTTPException(400, f"Keep the question under {MAX_CHARS} characters.")
    _charge(_client_ip(request))
    out = _answer(q)
    return {"answer": out["answer"], "sources": out["sources"], "route": out.get("route")}


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Football scouting assistant</title>
<style>
body{font:16px/1.55 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;color:#1b1f23}
h1{font-size:1.4rem;margin-bottom:.2rem} p.s{color:#555;margin-top:0}
textarea{width:100%;box-sizing:border-box;padding:.6rem;font:inherit;border:1px solid #bbb;border-radius:6px}
button{margin-top:.5rem;padding:.5rem 1rem;font:inherit;border:0;border-radius:6px;background:#1f5f3d;color:#fff;cursor:pointer}
button:disabled{opacity:.5}
#out{white-space:pre-wrap;margin-top:1.2rem;padding:1rem;border:1px solid #ddd;border-radius:6px;display:none}
#src{color:#555;font-size:.9rem;margin-top:.8rem}
.ex a{cursor:pointer;color:#1f5f3d;text-decoration:underline;display:block;margin:.2rem 0}
</style></head><body>
<h1>Football scouting assistant</h1>
<p class="s">Answers come from Transfermarkt season stats for nine leagues outside the top five, a few scouting notes and StatsBomb action descriptions. Every claim carries a source tag. If the data does not cover the question it says so.</p>
<textarea id="q" rows="3" maxlength="300" placeholder="Ask about players, leagues and seasons"></textarea>
<button id="go">Ask</button>
<div class="ex"><p class="s">Try:</p>
<a>Who scored the most goals in the Eredivisie (NL1) in 2023/24?</a>
<a>Which Liga Portugal (PO1) wingers under 23 had the best goal contributions per 90 in 2024/25?</a>
<a>Who will win the Eredivisie (NL1) next season?</a></div>
<div id="out"></div><div id="src"></div>
<script>
const q=document.getElementById('q'),go=document.getElementById('go'),out=document.getElementById('out'),src=document.getElementById('src');
document.querySelectorAll('.ex a').forEach(a=>a.onclick=()=>{q.value=a.textContent;q.focus()});
go.onclick=async()=>{go.disabled=true;out.style.display='block';out.textContent='Thinking...';src.textContent='';
try{const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q.value})});
const j=await r.json();if(!r.ok){out.textContent=j.detail||'Something went wrong.';}else{out.textContent=j.answer;src.textContent='Sources: '+(j.sources.join(', ')||'none');}}
catch(e){out.textContent='Could not reach the service.';}go.disabled=false;};
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE
