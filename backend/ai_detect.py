"""AI content detection using Claude Sonnet 4.5 via emergentintegrations."""
import os
import json
import re
import uuid
from emergentintegrations.llm.chat import LlmChat, UserMessage

SYSTEM = (
    "You are an expert AI-content detector for hiring assessments. "
    "Given a candidate's short-answer response, judge the probability (0-100) "
    "that it was AI-generated. Consider: uniform sentence rhythm, generic phrasing, "
    "over-formal transitions, lack of personal voice/specific examples, hedged claims, "
    "and encyclopedic tone. Respond ONLY as strict JSON: "
    '{"ai_risk_score": <int 0-100>, "confidence": "<low|medium|high>", '
    '"reasoning": "<one sentence>", "signals": ["<signal 1>", "<signal 2>"]}'
)


async def score_text_ai_risk(question: str, answer: str) -> dict:
    if not answer or len(answer.strip()) < 20:
        return {
            "ai_risk_score": 0,
            "confidence": "low",
            "reasoning": "Answer too short to analyze.",
            "signals": [],
        }

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {
            "ai_risk_score": -1,
            "confidence": "low",
            "reasoning": "LLM key not configured.",
            "signals": [],
        }

    chat = LlmChat(
        api_key=api_key,
        session_id=f"ai-detect-{uuid.uuid4().hex[:8]}",
        system_message=SYSTEM,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    prompt = f"Question:\n{question}\n\nCandidate answer:\n{answer}\n\nRespond as strict JSON only."
    try:
        text = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        return {
            "ai_risk_score": -1,
            "confidence": "low",
            "reasoning": f"Detection error: {str(e)[:120]}",
            "signals": [],
        }

    # Extract JSON from response
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {
            "ai_risk_score": -1,
            "confidence": "low",
            "reasoning": "Could not parse detector output.",
            "signals": [],
        }
    try:
        data = json.loads(match.group(0))
        score = int(data.get("ai_risk_score", 0))
        return {
            "ai_risk_score": max(0, min(100, score)),
            "confidence": data.get("confidence", "medium"),
            "reasoning": data.get("reasoning", ""),
            "signals": data.get("signals", []) if isinstance(data.get("signals"), list) else [],
        }
    except (ValueError, TypeError, json.JSONDecodeError):
        return {
            "ai_risk_score": -1,
            "confidence": "low",
            "reasoning": "Parse error.",
            "signals": [],
        }
