def get_thread_context(inbox: list, thread_id: str, current_timestamp: str) -> list:
    """
    Retrieves all prior messages in a thread to ground the LLM's response.
    """
    history = [
        msg for msg in inbox
        if msg.get("thread_id") == thread_id
        and msg.get("timestamp") < current_timestamp
    ]
    # Sort chronologically to maintain conversation flow
    return sorted(history, key=lambda x: x.get("timestamp", ""))

def format_context_for_prompt(history: list) -> str:
    """
    Formats the message history into a readable string for the LLM.
    """
    if not history:
        return "No prior thread context available."
        
    context_blocks = []
    for msg in history:
        context_blocks.append(
            f"--- Message ID: {msg['id']} ---\n"
            f"From: {msg['from']}\n"
            f"Date: {msg['timestamp']}\n"
            f"Body: {msg['body']}\n"
        )
    return "\n".join(context_blocks)