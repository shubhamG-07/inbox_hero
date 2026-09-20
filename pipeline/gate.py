import json
from datetime import datetime
from config import OUTBOX_DIR
from trace import log_event

# Explicit classification as required by the assignment manifest
IRREVERSIBLE_ACTIONS = ["send", "delete"]
REVERSIBLE_ACTIONS = ["draft", "archive", "defer", "label"]

def process_action(action_type: str, payload: dict, is_dry_run: bool) -> bool:
    """
    Gates irreversible actions. Reversible actions pass through automatically.
    Returns True if the action was executed/approved, False if denied/suppressed.
    """
    if action_type in REVERSIBLE_ACTIONS:
        print(f"[AUTO] Executed reversible action: {action_type}")
        return True

    if action_type not in IRREVERSIBLE_ACTIONS:
        print(f"Unknown action type: {action_type}")
        return False

    # Check the gate for irreversible actions
    print(f"\n[GATE] Proposed IRREVERSIBLE action: {action_type.upper()}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    decision = "denied"

    if is_dry_run:
        print("[GATE] DRY-RUN MODE: Action suppressed. No files written.")
        decision = "dry-run-suppressed"
    else:
        user_input = input("Approve this action? (y/n): ").strip().lower()
        if user_input == 'y':
            decision = "approved"
        else:
            print("[GATE] Action denied by user.")

    # Log the gate decision as required for Part 4 evidence
    log_event(
        cap_id="R3",
        event_type="gate",
        details={
            "proposed_action": action_type,
            "payload": payload,
            "decision": decision
        }
    )

    # Execute if approved
    if decision == "approved":
        if action_type == "send":
            _write_to_outbox(payload)
        elif action_type == "delete":
            print(f"[ACTION] Message {payload.get('target_id')} permanently deleted (mocked).")
        return True
        
    return False

def _write_to_outbox(payload: dict):
    """Writes an approved message to the outbox/ directory, one file per message."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    msg_id = payload.get("reply_to", "new")
    filename = OUTBOX_DIR / f"outbound_{msg_id}_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[OUTBOX] Message written to outbox/{filename.name}")