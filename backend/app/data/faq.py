"""
A small, hardcoded FAQ knowledge base standing in for a real help-center
export. In production this would be ingested from the company's actual
docs; the retrieval mechanism (services/faq_retrieval.py) doesn't care
where the text came from.
"""

FAQ_ENTRIES = [
    {
        "id": "faq_double_charge",
        "question": "Why was I charged twice for my subscription?",
        "answer": (
            "Duplicate charges usually happen when a renewal payment is "
            "retried after a brief processing delay, without the first "
            "attempt actually failing. Any duplicate charge is fully "
            "refundable - support can process it immediately once the "
            "duplicate transaction ID is confirmed on our end, typically "
            "within 3-5 business days to appear back on the card."
        ),
    },
    {
        "id": "faq_export_crash",
        "question": "Why does exporting to PDF crash the app?",
        "answer": (
            "PDF export crashes are most often caused by very large "
            "documents (100+ pages) or embedded high-resolution images "
            "exceeding available memory. A workaround is exporting in "
            "smaller sections. Our engineering team is tracking export "
            "stability as a known issue and prioritizes reports that "
            "include the document size and OS version."
        ),
    },
    {
        "id": "faq_account_lockout",
        "question": "How do I recover a locked account?",
        "answer": (
            "Accounts lock automatically after repeated failed login "
            "attempts as a security measure and unlock automatically "
            "after 30 minutes, or immediately via the 'Reset password' "
            "link on the login page, which sends a reset email."
        ),
    },
    {
        "id": "faq_invite_team",
        "question": "How do I invite team members to my workspace?",
        "answer": (
            "Team members can be invited from Settings > Team > Invite "
            "Member, by entering their email address. They'll receive an "
            "invite link that expires after 7 days. Workspace admins can "
            "resend or revoke pending invites from the same page."
        ),
    },
    {
        "id": "faq_dark_mode",
        "question": "Is there a dark mode?",
        "answer": (
            "Dark mode is not currently available but is one of the "
            "most-requested features and is on the product roadmap. "
            "There's no committed release date yet."
        ),
    },
    {
        "id": "faq_invoice_line_items",
        "question": "What does 'API overage' mean on my invoice?",
        "answer": (
            "An 'API overage' line item means usage exceeded the "
            "included monthly API call quota for the plan tier; overage "
            "is billed per additional 1,000 calls. Usage breakdowns are "
            "available under Billing > Usage History."
        ),
    },
]
