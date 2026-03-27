# main.py
import os
import json
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

# ایمپورت کردن گراف از فایل ایجنت‌ها
from agent import agent_graph 

load_dotenv(override=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clerk_config = ClerkConfig(jwks_url=os.getenv("CLERK_JWKS_URL"))
clerk_guard = ClerkHTTPBearer(clerk_config)

class ReportRequest(BaseModel):
    company: str

@app.post("/api/generate-report")
async def generate_report(
    request: ReportRequest, 
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard)
):
    user_id = creds.decoded["sub"]
    
    initial_state = {
        "company": request.company,
        "draft": "",
        "feedback": "اولین بار است که می‌نویسی. دقت کن حتما به ریسک‌ها اشاره کنی.",
        "is_approved": False
    }

    # موتور استریم حرفه‌ای (بدون دست زدن به کد agent)
    async def event_stream():
        # astream_events تمام اتفاقات داخل گراف رو به صورت زنده گزارش می‌ده
        async for event in agent_graph.astream_events(initial_state, version="v2"):
            
            # اگر رویداد مربوط به استریم شدن کلمات از سمت LLM بود:
            if event["event"] == "on_chat_model_stream":
                chunk_text = event["data"]["chunk"].content
                if chunk_text:
                    # ارسال کلمه به کلمه برای فرانت‌اند (استاندارد SSE)
                    # از json.dumps استفاده می‌کنیم تا کاراکترهای خاص (مثل اینتر) درست منتقل بشن
                    yield f"data: {json.dumps({'text': chunk_text})}\n\n"
            
            # (اختیاری) می‌تونی حتی آپدیت‌های گراف رو هم بفرستی تا فرانت‌اند بدونه الان کدوم ایجنت داره کار می‌کنه
            # elif event["event"] == "on_chain_start" and event["name"] == "auditor_node":
            #     yield f"data: {json.dumps({'status': 'Auditor is checking...'})}\n\n"
                
        # وقتی کار تموم شد، یک سیگنال پایان می‌فرستیم
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")