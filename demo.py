import json
import argparse
from config import INBOX_FILE
from pipeline.rules import triage_by_rules
from trace import log_event

def mock_llm_triage(message: dict) -> dict:
    """
    Placeholder for our future LLM call. 
    Right now, it just assumes anything that isn't a rule match needs to be escalated or replied to.
    """
    # We will replace this with an actual API call in the next step
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

        # Log to console
        print(f"{msg_id:<6} | {disposition:<10} | {reason[:40]}...")

        # Log to trace.jsonl as required for evidence
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
    
    # Assignment requirement: when the run finishes, no message is left without a disposition
    assert undecided_count == 0, "Failed R1: Some messages were left undecided!"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="inboxHero CLI")
    parser.add_argument("--cap", type=str, help="Capability to run (e.g., R1, R2)")
    
    args = parser.parse_args()

    if args.cap == "R1":
        run_r1_zero_inbox()
    else:
        print("Please specify a valid capability to run, e.g.: python demo.py --cap R1")