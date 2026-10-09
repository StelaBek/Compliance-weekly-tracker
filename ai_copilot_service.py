from __future__ import annotations
import asyncio, json, os
try:
    from copilot import CopilotClient
    from copilot.session import PermissionHandler
except Exception:
    CopilotClient=None; PermissionHandler=None

async def _ask(prompt:str)->str:
    token=os.environ.get("GITHUB_TOKEN")
    if not token: raise RuntimeError("GITHUB_TOKEN is not configured.")
    if CopilotClient is None: raise RuntimeError("github-copilot-sdk is not available in this environment.")
    client=CopilotClient(github_token=token,use_logged_in_user=False); await client.start()
    try:
        session=await client.create_session(model="auto",on_permission_request=PermissionHandler.approve_all)
        response=await session.send_and_wait(prompt)
        return response.data.content if response else ""
    finally:
        await client.stop()

def ask_copilot(prompt:str)->str: return asyncio.run(_ask(prompt))

def analyze_finding(record:dict)->str:
    fields=["id","jurisdiction","authority","source_name","source_url","original_title","english_title","publication_date","effective_date","compliance_deadline","legislative_status","instrument_type","compliance_domain","category","subcategory","affected_parties","key_obligations","key_changes","business_impact","recommended_follow_up","confidence_score","evidence_excerpt"]
    evidence={k:record.get(k) for k in fields}
    prompt=f'''You are a compliance intelligence copilot. Use ONLY the evidence below.
Return concise markdown with these headings:
**What changed**
**Who may be affected**
**What to inspect / verify**
**Recommended next action**
Rules:
- Never invent a law, deadline, tax rate, legislative reference, authority, product scope or applicability.
- If evidence is missing, say "Not established from the available evidence".
- Distinguish sourced facts from interpretation.
- Do not claim legal certainty.
- Keep it concise.
- End with: "AI-generated analysis. Informational only; not legal or tax advice."
EVIDENCE:
{json.dumps(evidence,ensure_ascii=False,default=str)}'''
    return ask_copilot(prompt)

def portfolio_brief(records:list[dict])->str:
    keys=["id","jurisdiction","english_title","compliance_domain","category","business_impact","compliance_deadline","key_changes","recommended_follow_up","source_url"]
    evidence=[{k:r.get(k) for k in keys} for r in records[:40]]
    prompt=f'''You are a compliance intelligence copilot. Write an executive portfolio analysis using ONLY the supplied records.
Use exactly these headings:
**AI view of the main themes**
**Items to prioritize**
**Questions for the compliance team**
Do not add external facts or unsupported dates. If the evidence is insufficient, say so.
End with: "AI-generated analysis. Informational only; not legal or tax advice."
EVIDENCE:
{json.dumps(evidence,ensure_ascii=False,default=str)}'''
    return ask_copilot(prompt)
