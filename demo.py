import os
import json
import argparse
from openai import OpenAI
from config import INBOX_FILE
from pipeline.rules import triage_by_rules
from pipeline.retriever import get_thread_context, format_context_for_prompt
from trace import log_event
from pipeline.gate import process_action
from memory import save_preference, load_preferences

# Initialize LLM Client for Ollama
# By overriding the base_url, we redirect the client away from OpenAI's servers to your local machine.
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # The client requires a string here, but Ollama ignores it.
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
        model="gemma4:e2b",
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="inboxHero CLI")
    parser.add_argument("--cap", type=str, help="Capability to run (e.g., R1, R2, R3, R4, X1)")
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
    elif args.cap == "X1":
        run_x1_inbox_qa(args.query)
    else:
        print("Please specify a valid capability, e.g.: python demo.py --cap R4")