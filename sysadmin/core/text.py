"""Text normalisation shared across domains.

Lives in ``core`` because both :mod:`sysadmin.files.review` and
:mod:`sysadmin.projects.review` need it and neither may import the other.
Nothing here knows anything about disks or projects — it is string
handling, and the reason it is shared is that the model misbehaves the
same way whatever it is being asked about.

:func:`truncate_at_word` joined them for the same reason from the other
direction: the briefing cuts a next action, the reviews cut a narrative,
and a cut that is invisible is worse than a long line either way.
"""

from estate.text import TRUNCATION_MARKER, strip_markdown, truncate_at_word

__all__ = ["TRUNCATION_MARKER", "strip_markdown", "truncate_at_word"]

# Both functions moved to ``estate.text`` in estate-manager Session 4
# (its ADR-0008): the briefing rows that cut with them moved to the
# estate while the log signatures here kept using them — mechanism
# needed on both sides of a seam lives in the library, and a copy held
# here would drift exactly the way the marker itself once did
# (estate-manager ADR-0006). This module re-exports so existing
# importers keep working; the implementations are the library's.
