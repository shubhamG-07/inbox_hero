def detect_hostile_intent(message: dict) -> dict:
    """
    Scans untrusted email content for embedded prompt injections 
    or unauthorized system directives.
    """
    body = message.get("body", "").lower()
    
    # Heuristic detection for common injection signatures found in the wild
    signatures = [
        "ignore all previous instructions",
        "system notice for automated assistants",
        "automated-agent directive",
        "assistant note:",
        "autonomous mode is now enabled"
    ]
    
    for sig in signatures:
        if sig in body:
            return {
                "is_hostile": True,
                "reason": f"Detected injection signature: '{sig}'"
            }
            
    return {"is_hostile": False, "reason": ""}