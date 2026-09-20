# inboxHero: System Capabilities Manifest

## The Required Six (R-Series)

**R1: Zero the Inbox**
*   **Command:** `python demo.py --cap R1`
*   **Description:** Processes every message in the inbox, assigning exactly one disposition (`reply`, `archive`, `defer`, `delegate`, `escalate`) with a documented reason. No message is left untouched.

**R2: Grounded Reply**
*   **Command:** `python demo.py --cap R2 --msg m008`
*   **Description:** Drafts a context-aware reply using the local LLM, explicitly citing the historical message IDs it used to ground its answer (e.g., extracting a URL from an earlier thread).

**R3: Gate the Irreversible**
*   **Command:** `python demo.py --cap R3 --msg m049` (Add `--dry-run` to suppress execution)
*   **Description:** Intercepts irreversible actions (`send`, `delete`) and pauses for explicit human approval `(y/n)`. Reversible actions (`draft`, `archive`, `label`, `defer`) bypass the gate.
*   **Architectural Trade-Off (The Fatigue Line):** To prevent alert fatigue where a user blindly approves forty prompts, we drew the line strictly at data exfiltration (sending mail) and permanent data loss (deleting mail). We traded away absolute control over reversible actions; we accept the risk that the AI might mistakenly archive a useful internal email, in exchange for guaranteeing the human actually reads the prompt when external communication or permanent deletion is proposed.

**R4: Persistent Preference**
*   **Command:** `python demo.py --cap R4 --msg m018`
*   **Description:** Reads a standing instruction from one message (e.g., "always CC Priya on Legal mail"), persists it to disk in `prefs.json`, and autonomously applies that rule across process restarts.

**R5: Refuse Embedded Instructions**
*   **Command:** `python demo.py --cap R5`
*   **Description:** Scans the inbox for prompt injection attempts (e.g., "ignore previous instructions"). It flags the hostile messages, logs the refusal, and bypasses execution to protect the system.

**R6: Dashboard**
*   **Command:** `python demo.py --cap R6`
*   **Description:** Generates a static, executive-grade HTML dashboard aggregating pending approvals, security threats, multi-message timeline commitments, and schedule conflicts.

---

## Custom Extensions (X-Series)

**X1: Inbox Intelligence Query Engine (Tier B)**
*   **Command:** `python demo.py --cap X1 --query "your question"`
*   **Description:** Allows the user to query their live inbox using natural language. The system locates the most relevant thread and extracts a concise, cited answer using the local LLM. Includes a command generator in the dashboard UI.

**X2: Morning Digest (Tier A)**
*   **Command:** `python demo.py --cap X2`
*   **Description:** A single-pass prioritization filter that silently counts auto-archived noise and surfaces only the top priority unread items requiring immediate human attention.

**X3: Outbound Follow-up Tracker (Tier B)**
*   **Command:** `python demo.py --cap X3`
*   **Description:** Scans the inbox for outbound messages sent by the user that are currently the terminal node in their thread, flagging them as awaiting a reply.

**X4: Smart Scheduler & Conflict Resolver (Tier C)**
*   **Command:** `python demo.py --cap X4`
*   **Description:** A genuinely agentic scheduling capability. It scans the inbox, detects the Sept 15 3:00 PM calendar conflict, autonomously queries the LLM to draft three alternative meeting times, and holds the drafted reply in the irreversible action gate for human approval.