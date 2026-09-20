    
## Architectural Reflections

**1. What did you refuse to automate?**
I deliberately refused to automate the sending of calendar conflict resolutions, such as the drafted alternatives for message `m010` in my X4 Smart Scheduler capability. The line is drawn strictly at irreversible state changes—like data exfiltration (sending mail) or permanent data loss (deleting mail)—which must pass through the `process_action` human-in-the-loop gate (R3). While I accept the risk of the AI mistakenly archiving a benign internal email, I refuse to let it autonomously commit the user's schedule or external reputation without explicit `(y/n)` human approval.

**2. Where does untrusted text enter your system?**
Untrusted text enters the system exclusively through the `subject` and `body` fields parsed from the incoming `inbox.json` file. The boundary between read text and executable instructions is structural; these fields are routed through the deterministic `detect_hostile_intent` Python function (R5) before they are ever formatted into an LLM prompt. To make the system act on their behalf, an attacker would have to defeat both this hardcoded Python heuristic scanner and the rigid JSON-schema enforcer that isolates the user prompt payload from the core system instructions.

**3. Who is accountable when it sends the wrong thing?**
The human operator remains entirely accountable for any badly worded, factually incorrect, or misrouted message sent in their name. Because the system utilizes the `process_action` gate for all irreversible actions, the AI functions strictly as a high-leverage drafter, transferring the final responsibility of review to the human pressing 'y'. If a failure occurs, the system provides full traceability through the `trace.jsonl` event log, which records the exact LLM prompt used, the context cited, and the precise timestamp the human approved the transmission.

**4. Name your own machinery.**
In my architecture, the direct API calls to the local Gemma model act as the "Agent", the individual Python functions like `run_x4_smart_scheduler` represent the "Tasks", the sequential execution inside `demo.py` orchestrates the "Crew", and the `argparse` `if/elif` block serves as the router. A framework like LangChain would have provided built-in memory management and tool-calling abstractions, which I built manually using the `prefs.json` file cache. Building this manually ultimately helped the project; relying on heavy framework abstractions would have obscured the data flow, making it significantly harder to implement precise security gates and isolate prompt injection defenses.

## System Architecture

**inboxHero** is a local-first, autonomous email triage agent built in native Python without relying on heavy, opaque agentic frameworks. The architecture is designed around a strict, privacy-preserving pipeline: incoming email data (`inbox.json`) is processed through a deterministic heuristic security scanner to intercept prompt injections before they ever reach the local LLM reasoning engine (Gemma via Ollama). System state and persistent context are maintained in a lightweight, file-based memory cache (`prefs.json`). Finally, to prevent autonomous failure, all irreversible state changes (e.g., sending or deleting mail) are aggressively routed through a human-in-the-loop approval gate, ensuring the system operates as a high-leverage drafter rather than an unsupervised actor.

```mermaid
graph TD
    %% Define Styles
    classDef file fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef process fill:#0f172a,stroke:#64748b,stroke-width:1px,color:#fff;
    classDef security fill:#450a0a,stroke:#ef4444,stroke-width:2px,color:#fff;
    classDef llm fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef human fill:#422006,stroke:#f59e0b,stroke-width:2px,color:#fff;

    %% Nodes
    Inbox([inbox.json]):::file
    Router(CLI Router / demo.py):::process
    Scanner{Security Gate R5}:::security
    Memory[(prefs.json)]:::file
    LLM(Ollama: Gemma LLM):::llm
    ActionGate{Action Type}:::process
    HumanGate{Human Approval R3}:::human
    Dashboard([dashboard.html]):::file
    Outbox([outbox.json]):::file

    %% Flow
    Inbox --> Router
    Router --> Scanner
    Scanner -- "Hostile/Phishing" --> Dashboard
    Scanner -- "Safe Context" --> LLM
    
    LLM <--> |"Read/Write Context"| Memory
    LLM --> ActionGate
    
    ActionGate -- "Reversible (Draft, Archive)" --> Dashboard
    ActionGate -- "Irreversible (Send, Delete)" --> HumanGate
    
    HumanGate -- "(Y) Approved" --> Outbox
    HumanGate -- "(N) Denied" --> Dashboard