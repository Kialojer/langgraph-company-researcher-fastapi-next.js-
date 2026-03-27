# agent.py
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv(override=True)


class ReportState(TypedDict):
    company: str
    draft: str
    feedback: str
    is_approved: bool

# نکته: برای استریم کردن، فقط مطمئن شو از مدل درستی استفاده می‌کنی
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def analyst_node(state: ReportState):
    company = state["company"]
    feedback = state.get("feedback", "") 
    
    prompt = f"""
        You are a financial analyst. Write a short two-line report about {company}.
        Note: The company's auditor has noted this issue in your previous report: '{feedback}'.
        Please correct the report.
    """
    response = llm.invoke(prompt)
    return {"draft": response.content}

def auditor_node(state: ReportState):
    draft = state["draft"]
    if "risk" in draft.lower() or "ریسک" in draft:
        return {"is_approved": True, "feedback": "عالی بود، تایید شد."}
    else:
        return {"is_approved": False, "feedback": "رد شد! حتماً باید درباره ریسک‌های سرمایه‌گذاری هشدار بدی."}

def review_router(state: ReportState):
    if state["is_approved"] == True:
        return "END" 
    else:
        return "analyst" 

# ساخت گراف
builder = StateGraph(ReportState)
builder.add_node("analyst", analyst_node)
builder.add_node("auditor", auditor_node)
builder.add_edge(START, "analyst")
builder.add_edge("analyst", "auditor")
builder.add_conditional_edges(
    "auditor",
    review_router,
    {"END": END, "analyst": "analyst"}
)

# ما این متغیر رو به دنیای بیرون (فایل main) اکسپورت می‌کنیم
agent_graph = builder.compile()