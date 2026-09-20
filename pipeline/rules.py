def triage_by_rules(message: dict) -> dict:
    """
    Evaluates a message against deterministic rules.
    Returns a dict with 'disposition' and 'reason' if matched, else None.
    """
    sender = message.get("from", "").lower()
    subject = message.get("subject", "").lower()
    body = message.get("body", "").lower()

    # 1. Receipts and Invoices
    if any(keyword in sender for keyword in ["receipts@", "billing@", "orders@", "invoice@"]) or \
       any(keyword in subject for keyword in ["receipt", "invoice", "order confirmed", "bill"]):
        return {
            "disposition": "archive",
            "reason": "Rule match: Automated receipt/billing"
        }

    # 2. Automated System Notifications
    if any(keyword in sender for keyword in ["no-reply@", "noreply@", "notifications@", "alerts@"]):
        # Exception: Don't auto-archive security alerts (like new logins or password changes)
        if "security" not in sender and "password" not in subject and "verification" not in subject and "login" not in subject:
             return {
                "disposition": "archive",
                "reason": "Rule match: Automated system notification"
            }

    # 3. Newsletters and Digests
    if "digest" in subject or "newsletter" in sender or "unsubscribe" in body:
        return {
            "disposition": "archive",
            "reason": "Rule match: Newsletter or digest"
        }
        
    # 4. Calendar Reminders
    if "calendar-notification@google.com" in sender or "calendly.com" in sender:
        return {
            "disposition": "archive",
            "reason": "Rule match: Calendar auto-reminder"
        }

    # No rule matched; this message requires an LLM
    return None 