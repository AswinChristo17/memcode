"""
memcode/wrapper.py
Calls OpenCode CLI with the augmented prompt and captures its response.
"""
import subprocess
import json
import shutil
from typing import Optional

from memcode.config import OPENCODE_BIN


class OpenCodeNotFoundError(Exception):
    pass


class OpenCodeError(Exception):
    def __init__(self, message: str, returncode: int, stderr: str):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def _check_opencode():
    if not shutil.which(OPENCODE_BIN):
        raise OpenCodeNotFoundError(
            f"'{OPENCODE_BIN}' not found on PATH.\n"
            "Install it first: https://opencode.ai\n"
            "Or set OPENCODE_BIN env var to the full path."
        )


def run(prompt: str, cwd: Optional[str] = None) -> str:
    """
    Run opencode with the given prompt.
    Passes the prompt via stdin to avoid command-line length issues
    and interactive mode problems.
    Uses: opencode run --format json (with prompt on stdin)
    """
    _check_opencode()

    cmd = [
        OPENCODE_BIN,
        "run",
        "--format", "json",
    ]

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120,  # 2 minute timeout (OpenCode startup can be slow on first run)
            encoding='utf-8',
            errors='replace',  # Replace invalid characters instead of failing
        )
    except subprocess.TimeoutExpired:
        raise OpenCodeError(
            "OpenCode timed out after 2 minutes.\n"
            "This can happen if:\n"
            "  • OpenCode is still starting up (first run is slower)\n"
            "  • Your internet is slow (OpenCode calls external APIs)\n"
            "  • The model API is overloaded\n"
            "Try again in a moment.",
            -1,
            ""
        )

    if result.returncode != 0:
        raise OpenCodeError(
            f"OpenCode exited with code {result.returncode}",
            result.returncode,
            result.stderr or "No error message",
        )

    if not result.stdout:
        raise OpenCodeError(
            "OpenCode returned empty output",
            result.returncode,
            result.stderr or "No error details available"
        )

    output = result.stdout.strip()
    return _parse_output(output)


def _parse_output(output: str) -> str:
    """
    Parse OpenCode JSON event stream output.
    Events with type "text" contain part.text — that's the assistant response.
    Falls back to raw output if no valid JSON found.
    """
    if not output:
        raise OpenCodeError("OpenCode returned empty output", -1, "")

    texts = []
    has_json = False
    
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            has_json = True
            if event.get("type") == "text":
                text = event.get("part", {}).get("text", "")
                if text:
                    texts.append(text)
        except (json.JSONDecodeError, AttributeError, TypeError):
            # Not JSON, might be plain text output
            if not has_json:
                texts.append(line)

    if texts:
        return "\n".join(texts)

    # If we got here with no text extracted, return the raw output
    # (better than failing silently)
    return output