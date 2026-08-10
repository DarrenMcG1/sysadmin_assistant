"""Text normalisation shared by the LLM-narrated reviews.

Lives in ``core`` because both :mod:`sysadmin.files.review` and
:mod:`sysadmin.projects.review` need it and neither may import the other.
Nothing here knows anything about disks or projects — it is string
handling, and the reason it is shared is that the model misbehaves the
same way whatever it is being asked about.
"""

import re


def strip_markdown(text: str) -> str:
    """Remove heading, list and emphasis markers the model was told not to emit.

    Instructions are a request, not a constraint. Verified live
    2026-08-06: under an explicit "no markdown, no headings, no numbered
    or bulleted lists" instruction, dria-agent-a-3b produced
    ``### Where the Mess is Coming From``, then ``1. **Node_modules
    directories**:`` on the next attempt. Stripping is deterministic, so
    the stored narrative matches the plain-text format the briefing and
    tray expect whatever the model does.

    Markers are only recognised at the start of a line, so prose keeps
    its hyphens and any inline asterisks.
    """
    cleaned = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
        elif stripped.startswith(("- ", "* ", "+ ")):
            stripped = stripped[2:].strip()
        else:
            # "1. ", "2) " — an ordered list the model was asked not to use
            stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
        cleaned.append(stripped.replace("**", ""))
    return "\n".join(cleaned).strip()
