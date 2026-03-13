"""
memcode/prompt.py
Builds the augmented prompt by appending memory context after the user's request.
"""
from memcode.memory import build_memory_context


def build_prompt(user_message: str) -> tuple[str, bool]:
    """
    Returns (augmented_prompt, had_memories).
    Memory context is prepended BEFORE the request so the LLM sees the
    personal facts first and can use them accurately.
    """
    context = build_memory_context(user_message)

    if not context:
        return user_message, False

    augmented = (
        f"IMPORTANT: The following is verified information from previous conversations "
        f"with this user. Answer personal questions using ONLY this context — do NOT say "
        f"you have no memory or that sessions start fresh.\n\n"
        f"{context}\n"
        f"User's current message: {user_message}"
    )
    return augmented, True