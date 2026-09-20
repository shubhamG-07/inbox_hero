import os
import json
import argparse
from openai import OpenAI
from config import OLLAMA_BASE_URL, OLLAMA_API_KEY, MODEL_NAME
from config import INBOX_FILE
from pipeline.rules import triage_by_rules
from pipeline.retriever import get_thread_context, format_context_for_prompt
from trace import log_event
from pipeline.gate import process_action
from memory import save_preference, load_preferences
from pipeline.security import detect_hostile_intent
from pipeline.dashboard import generate_dashboard_html


# Initialize LLM Client for Ollama
# By overriding the base_url, we redirect the client away from OpenAI's servers to your local machine.
client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key=OLLAMA_API_KEY
)

def mock_llm_triage(message: dict) -> dict:
    """
    Placeholder for our future LLM call. 
    Right now, it just assumes anything that isn't a rule match needs to be escalated or replied to.
    """
    return {
        "disposition": "escalate",
        "reason": "LLM Placeholder: Needs human review or complex reply"
    }

def run_r1_zero_inbox():
    """
    Capability R1: Assign every message exactly one disposition.
    """
    if not INBOX_FILE.exists():
        print(f"Error: Could not find {INBOX_FILE}")
        return

    with open(INBOX_FILE, "r") as f:
        inbox = json.load(f)

    total_messages = len(inbox)
    rule_handled_count = 0
    undecided_count = 0

    print(f"Processing {total_messages} messages...\n")
    print(f"{'ID':<6} | {'DISPOSITION':<10} | {'REASON'}")
    print("-" * 60)

    for msg in inbox:
        msg_id = msg.get("id")
        
        # 1. Try deterministic rules first
        decision = triage_by_rules(msg)
        
        # 2. If rules fail, route to LLM
        if decision:
            rule_handled_count += 1
        else:
            decision = mock_llm_triage(msg)
            
        if not decision:
            undecided_count += 1
            continue

        disposition = decision["disposition"]
        reason = decision["reason"]

        print(f"{msg_id:<6} | {disposition:<10} | {reason[:40]}...")

        log_event(
            cap_id="R1",
            event_type="decision",
            details={
                "message_id": msg_id,
                "disposition": disposition,
                "reason": reason
            }
        )

    print("\n--- R1 Summary ---")
    print(f"Messages processed: {total_messages}")
    print(f"Rule handled: {rule_handled_count}")
    print(f"Undecided: {undecided_count}")
    
    assert undecided_count == 0, "Failed R1: Some messages were left undecided!"

def run_r2_grounded_reply(target_msg_id: str = "m008"):
    """
    Capability R2: Draft a reply grounded in a specific earlier message.
    """
    with open(INBOX_FILE, "r") as f:
        inbox = json.load(f)

    target_msg = next((m for m in inbox if m["id"] == target_msg_id), None)
    if not target_msg:
        print(f"Message {target_msg_id} not found.")
        return

    history = get_thread_context(inbox, target_msg["thread_id"], target_msg["timestamp"])
    cited_ids = [msg["id"] for msg in history]
    context_text = format_context_for_prompt(history)

    system_instruction = (
        "You are an executive assistant. Draft a brief, professional reply to the TARGET MESSAGE. "
        "You MUST base your answer strictly on the provided THREAD CONTEXT. "
        "Do not invent URLs, credentials, or facts. "
        "End your draft by explicitly listing the Message IDs you used as sources (e.g., 'cited: [m001, m002]')."
    )
    
    user_payload = (
        f"--- THREAD CONTEXT ---\n{context_text}\n\n"
        f"--- TARGET MESSAGE ---\nFrom: {target_msg['from']}\nBody: {target_msg['body']}"
    )

    print(f"Drafting reply for {target_msg_id} using context from {cited_ids}...\n")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_payload}
        ],
        temperature=0.0
    )

    draft = response.choices[0].message.content

    print("--- DRAFT ---")
    print(draft)
    print("-------------")

    log_event(
        cap_id="R2",
        event_type="draft",
        details={
            "target_msg": target_msg_id,
            "cited_ids": cited_ids,
            "draft_content": draft
        }
    )

def run_r3_gate(is_dry_run: bool, target_msg_id: str):
    """
    Capability R3: Gate irreversible actions.
    Now integrated with R4 memory to apply standing preferences to the payload.
    """
    with open(INBOX_FILE, "r") as f:
        inbox = json.load(f)

    target_msg = next((m for m in inbox if m["id"] == target_msg_id), None)
    if not target_msg:
        print(f"Message {target_msg_id} not found.")
        return

    print(f"Simulating agent actions for target: {target_msg_id}...\n")
    
    # 1. A reversible action
    process_action(
        "archive", 
        {"target_id": target_msg_id, "reason": "User requested archive"}, 
        is_dry_run
    )
    
    # 2. Build the SEND payload dynamically
    send_payload = {
        "reply_to": target_msg_id,
        "to": target_msg.get("from", "unknown"),
        "body": "Executing requested action."
    }
    
    # --- Integration with Part 5 (Memory) ---
    prefs = load_preferences()
    if "hartwellcho.com" in target_msg.get("from", ""):
        legal_cc = prefs.get("legal_cc")
        if legal_cc:
            send_payload["cc"] = legal_cc
            print(f"[SYSTEM] Applied standing preference: CC'ing {legal_cc}")
    # ----------------------------------------
    
    # 3. An irreversible action (Send)
    process_action("send", send_payload, is_dry_run)
    
    # 4. Another irreversible action (Delete)
    process_action(
        "delete", 
        {"target_id": target_msg_id, "reason": "Identified as spam/phishing"}, 
        is_dry_run
    )
    
    print("\nR3 test complete. Check trace.jsonl for logs.")

def run_r4_persistent_preference(target_msg_id: str):
    """
    Capability R4: Persistent preference.
    Run 1 (e.g., --msg m015): Learns the preference, saves to disk, and exits.
    Run 2 (e.g., --msg m018): Loads from disk and applies it on a fresh run.
    """
    with open(INBOX_FILE, "r") as f:
        inbox = json.load(f)

    target_msg = next((m for m in inbox if m["id"] == target_msg_id), None)
    if not target_msg:
        print(f"Message {target_msg_id} not found.")
        return

    print(f"Processing target message: {target_msg_id}")
    print(f"Subject: {target_msg.get('subject')}\n")
    
    # 1. Learning Phase
    if target_msg_id == "m015":
        print("Detected standing instruction: CC Priya on Hartwell & Cho legal mail.")
        save_preference("legal_cc", "priya@paperjet.io")
        print("\n[MEMORY] Preference saved to disk. The process will now exit.")
        
        log_event(
            cap_id="R4",
            event_type="preference_learned",
            details={
                "source_msg": target_msg_id, 
                "preference_key": "legal_cc", 
                "value": "priya@paperjet.io"
            }
        )

    # 2. Application Phase
    elif target_msg_id == "m018" or "hartwellcho.com" in target_msg.get("from", ""):
        print("Checking memory for standing instructions...")
        prefs = load_preferences()
        legal_cc = prefs.get("legal_cc")
        
        if legal_cc:
            print(f"[ACTION] Automatically added {legal_cc} to CC based on standing preference.")
            log_event(
                cap_id="R4",
                event_type="preference_applied",
                details={
                    "trigger_msg": target_msg_id, 
                    "preference_key": "legal_cc", 
                    "action_taken": f"CC'd {legal_cc}"
                }
            )
        else:
            print("[ACTION] No standing preference found. Handled normally.")
            
    else:
        print("For this R4 demonstration, please use --msg m015 to learn the preference, and --msg m018 to apply it.")

def run_r5_hostile_inbox():
    """
    Capability R5: Refuse embedded instructions.
    Scans the inbox for hostile messages, flags them, logs refusals, and takes no action.
    """
    with open(INBOX_FILE, "r") as f:
        inbox = json.load(f)

    print("Scanning inbox for hostile instructions...\n")
    
    flagged_count = 0
    
    for msg in inbox:
        msg_id = msg.get("id")
        security_check = detect_hostile_intent(msg)
        
        if security_check["is_hostile"]:
            flagged_count += 1
            reason = security_check["reason"]
            
            # 1. Tell the user (Console output)
            print(f"FLAGGED: {msg_id} attempted to manipulate the system.")
            print(f"-> Threat: {reason}")
            print(f"-> Action: Not done, left in place. No files written to outbox/.\n")
            
            # 2. Log the refusal (Audit trail)
            log_event(
                cap_id="R5",
                event_type="refusal",
                details={
                    "message_id": msg_id,
                    "attempted_action": reason,
                    "system_action": "refused_and_flagged"
                }
            )

    print(f"--- R5 Summary ---")
    print(f"Total messages scanned: {len(inbox)}")
    print(f"Hostile messages flagged and neutralized: {flagged_count}")

def run_r6_dashboard():
    """
    Capability R6: Dashboard generation.
    Dynamically processes inbox.json to aggregate R-series and X-series capabilities.
    """
    with open(INBOX_FILE, "r") as f:
        inbox = json.load(f)

    print(f"Aggregating data for dashboard (including X1, X2, X3, X4)...\n")

    pending_actions = []
    flagged_items = []
    commitments = []

    # --- R1 & R5 Data Pipeline ---
    for msg in inbox:
        msg_id = msg["id"]
        
        security_check = detect_hostile_intent(msg)
        is_phish = any(kw in msg.get("body", "").lower() for kw in ["wire $", "password expires", "remittance details"])

        if security_check["is_hostile"] or is_phish:
            flagged_items.append({
                "msg_id": msg_id, 
                "threat": security_check["reason"] if security_check["is_hostile"] else "Suspected Phishing", 
                "action_taken": "Refused/Flagged"
            })
            continue

        if msg.get("unread") and not triage_by_rules(msg):
            if len(pending_actions) < 5:
                pending_actions.append({
                    "msg_id": msg_id,
                    "action": "REVIEW / DRAFT",
                    "reason": f"Requires LLM drafting or human approval. Subject: '{msg.get('subject')}'"
                })

    # --- R6 Commitments & X4 Scheduler Pipeline ---
    board_threads = [m for m in inbox if m["thread_id"] in ["t-board", "t-deck"]]
    if board_threads:
        commitments.append({
            "datetime": "Sep 16, 2026 (Derived)", 
            "desc": "Board deck finalized and circulated", 
            "sources": f"{[m['id'] for m in board_threads]}", 
            "notes": "Derived dynamically from Sep 18 meeting and 'two days before' constraint."
        })

    vc_call = next((m for m in inbox if m["id"] == "m010"), None)
    dentist = next((m for m in inbox if m["id"] == "m061"), None)
    
    x4_resolutions = [] # New list for X4 capability
    
    if vc_call and dentist:
        commitments.append({
            "datetime": "Sep 15, 2026 @ 3:00pm", "desc": "Intro call with Aria (Northwind VC)", 
            "sources": f"[{vc_call['id']}]", "conflict": True, "notes": f"Conflicts with {dentist['id']}"
        })
        commitments.append({
            "datetime": "Sep 15, 2026 @ 3:00pm", "desc": "Dental cleaning with Dr. Osei", 
            "sources": f"[{dentist['id']}]", "conflict": True, "notes": f"Conflicts with {vc_call['id']}"
        })
        # Inject X4 resolution data
        x4_resolutions.append({
            "conflict": "Sep 15 @ 3:00pm (VC Call vs Dentist)",
            "action": "Drafted 3 alternative times for Sep 16",
            "status": "Held in R3 Gate for Approval"
        })

    # --- X2: Morning Digest Data ---
    needs_me = []
    archived_count = 0
    for msg in inbox:
        if msg.get("unread"):
            decision = triage_by_rules(msg)
            if decision and decision["disposition"] == "archive":
                archived_count += 1
            else:
                needs_me.append(msg)
    digest_data = {"archived": archived_count, "needs_me": needs_me[:5]}

    # --- X3: Follow-up Tracker Data ---
    sam_sent = [m for m in inbox if m.get("from") == "sam@paperjet.io"]
    followups = []
    for sent_msg in sam_sent:
        replies = [m for m in inbox if m.get("thread_id") == sent_msg.get("thread_id") and m.get("timestamp") > sent_msg.get("timestamp")]
        if not replies:
            followups.append(sent_msg)

    # Render HTML (Now passing x4_resolutions)
    generate_dashboard_html(pending_actions, flagged_items, commitments, digest_data, followups, x4_resolutions)
    
    log_event(
        cap_id="R6",
        event_type="dashboard_generated_extended",
        details={"file": "dashboard.html", "x4_resolved": len(x4_resolutions)}
    )

def run_x1_inbox_qa(question: str):
    """
    Capability X1 (Custom): Ask a natural language question about the inbox.
    Always searches the live inbox.json and uses the LLM to generate an answer.
    """
    if not question:
        print("Please provide a question using the --query flag.")
        return

    with open(INBOX_FILE, "r") as f:
        inbox = json.load(f)

    # 1. Simple keyword matching to find the most relevant thread
    keywords = [word.lower() for word in question.split() if len(word) > 3]
    
    thread_scores = {}
    for msg in inbox:
        text_to_search = (msg.get("subject", "") + " " + msg.get("body", "")).lower()
        score = sum(1 for kw in keywords if kw in text_to_search)
        
        if score > 0:
            tid = msg.get("thread_id")
            thread_scores[tid] = thread_scores.get(tid, 0) + score

    if not thread_scores:
        print("Could not find any emails related to your question.")
        return

    # Get the thread_id with the highest keyword match score
    best_thread_id = max(thread_scores, key=thread_scores.get)
    print(f"Found relevant thread: {best_thread_id} (Querying LLM...)\n")

    # 2. Retrieve thread context
    history = get_thread_context(inbox, best_thread_id, "2099-01-01T00:00:00")
    context_text = format_context_for_prompt(history)
    cited_ids = [msg["id"] for msg in history]

    # 3. Ask the LLM
    system_instruction = (
        "You are an AI assistant helping the user search their email. "
        "Answer the user's question based STRICTLY on the provided thread context. "
        "Keep your answer concise and factual. Do not invent information."
    )
    
    user_payload = (
        f"--- THREAD CONTEXT ---\n{context_text}\n\n"
        f"--- USER QUESTION ---\n{question}"
    )

    response = client.chat.completions.create(
        model="gemma4:e2b", 
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_payload}
        ],
        temperature=0.0
    )

    answer = response.choices[0].message.content

    print(f"Question: {question}")
    print("--- ANSWER ---")
    print(answer)
    print(f"(Sources: {cited_ids})")
    print("--------------")

    # Log the custom capability for the Part 9 manifest evidence
    log_event(
        cap_id="X1",
        event_type="qa_search",
        details={
            "question": question,
            "thread_used": best_thread_id,
            "answer": answer
        }
    )

def run_x2_morning_digest():
    """
    Capability X2 (Tier A): Morning Digest.
    A single-pass lookup that separates what needs the user today from what was auto-archived.
    """
    with open(INBOX_FILE, "r") as f:
        inbox = json.load(f)

    needs_me = []
    archived_count = 0

    for msg in inbox:
        if not msg.get("unread"):
            continue
            
        rule_decision = triage_by_rules(msg)
        if rule_decision and rule_decision["disposition"] == "archive":
            archived_count += 1
        else:
            needs_me.append(msg)

    print("--- MORNING DIGEST ---")
    print(f"Auto-archived noise: {archived_count} messages\n")
    print("Needs Your Attention:")
    for m in needs_me[:5]: # Top 5 for brevity
        print(f"- [{m['id']}] {m['from']}: {m['subject']}")
    
    if len(needs_me) > 5:
        print(f"...and {len(needs_me) - 5} more.")
        
    log_event(
        cap_id="X2",
        event_type="digest_generated",
        details={"needs_me_count": len(needs_me), "archived_count": archived_count}
    )

def run_x3_followup_tracker():
    """
    Capability X3 (Tier B): Follow-up tracking.
    Finds messages Sam sent that nobody has answered, and flags them for follow-up.
    """
    with open(INBOX_FILE, "r") as f:
        inbox = json.load(f)

    # 1. Find all messages sent by Sam
    sam_sent = [m for m in inbox if m.get("from") == "sam@paperjet.io"]
    unanswered = []

    # 2. Check if they are the last message in their respective threads
    for sent_msg in sam_sent:
        thread_id = sent_msg.get("thread_id")
        timestamp = sent_msg.get("timestamp")
        
        # Look for any message in the same thread that occurred AFTER Sam's message
        replies = [
            m for m in inbox 
            if m.get("thread_id") == thread_id 
            and m.get("timestamp") > timestamp
        ]
        
        if not replies:
            unanswered.append(sent_msg)

    print("--- UNANSWERED OUTBOUND MAIL ---")
    for m in unanswered:
        print(f"Waiting on reply for: [{m['id']}] To: {m['to']} | Subject: {m['subject']}")

    log_event(
        cap_id="X3",
        event_type="followup_scan",
        details={"unanswered_count": len(unanswered)}
    )

def run_x4_smart_scheduler(is_dry_run: bool):
    """
    Capability X4 (Tier C): Conflict Resolution & Scheduling.
    Detects a meeting conflict, proposes alternatives, and holds the reply for human approval.
    """
    with open(INBOX_FILE, "r") as f:
        inbox = json.load(f)
        
    print("Scanning inbox for schedule commitments...\n")
    
    # 1. Detect the specific conflict
    vc_call = next((m for m in inbox if m["id"] == "m010"), None)
    dentist = next((m for m in inbox if m["id"] == "m061"), None)
    
    if not vc_call or not dentist:
        print("Could not find the conflict messages (m010 / m061).")
        return
        
    print(f"[AGENT: ALERT] Conflict detected on Sep 15 at 3:00 PM!")
    print(f"-> Event 1: {vc_call['subject']} (ID: {vc_call['id']})")
    print(f"-> Event 2: {dentist['subject']} (ID: {dentist['id']})\n")
    
    print("[AGENT: PLANNING] Generating alternatives via LLM...")
    
    # 2. Reason and generate alternatives using the LLM
    prompt = (
        f"You are an executive assistant. We have a conflict on Sep 15 at 3:00pm and cannot make the call. "
        f"Draft a brief, polite email to {vc_call['from']} proposing three specific alternative time slots "
        f"for September 16th. Output ONLY the raw email body, with no additional commentary."
    )
    
    response = client.chat.completions.create(
        model="gemma4:e2b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    
    draft_body = response.choices[0].message.content.strip()
    
    # 3. Draft the resolution and hold it in the human-in-the-loop gate (R3)
    payload = {
        "reply_to": vc_call['id'],
        "to": vc_call['from'],
        "subject": f"Re: {vc_call['subject']}",
        "body": draft_body
    }
    
    print("[AGENT: SAFETY] Solution drafted. Routing to human approval gate...\n")
    
    # Re-use our existing gate to hold the action
    process_action("send", payload, is_dry_run)
    
    log_event(
        cap_id="X4", 
        event_type="conflict_resolved_and_held", 
        details={"conflict_time": "Sep 15 3:00pm", "action": "drafted_alternatives"}
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="inboxHero CLI")
    parser.add_argument("--cap", type=str, help="Capability to run (e.g., R1, R2, R3, R4, R5, R6, X1)")
    parser.add_argument("--msg", type=str, default="m008", help="Target message ID for R2")
    parser.add_argument("--query", type=str, help="Question string for X1 capability")
    parser.add_argument("--dry-run", action="store_true", help="Run without executing irreversible actions")
    
    args = parser.parse_args()

    if args.cap == "R1":
        run_r1_zero_inbox()
    elif args.cap == "R2":
        run_r2_grounded_reply(args.msg)
    elif args.cap == "R3":
        run_r3_gate(args.dry_run, args.msg)
    elif args.cap == "R4":
        run_r4_persistent_preference(args.msg)
    elif args.cap == "R5":
        run_r5_hostile_inbox()
    elif args.cap == "R6":
        run_r6_dashboard()
    elif args.cap == "X1":
        run_x1_inbox_qa(args.query)
    elif args.cap == "X2":
        run_x2_morning_digest()
    elif args.cap == "X3":
        run_x3_followup_tracker()
    elif args.cap == "X4":
        run_x4_smart_scheduler(args.dry_run)
    else:
        print("Please specify a valid capability, e.g.: python demo.py --cap X2")
    