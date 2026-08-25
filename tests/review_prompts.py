"""The one statement of rule 2, shared by the three Tier 3 reviews.

Three modules build an LLM-narrated weekly review — ``log_review``,
``files.review`` and ``health_review`` — and all three rest on the same
rule: **no digit reaches the model from the data**.  It was learned
twice at the cost of a live debugging session.  Session 23 handed
dria-agent-a-3b scores and told it not to restate them, and it restated
them; Session 24 handed it "25.0 GB across 50 directories" with the same
instruction, and it restated *and* derived "each consuming 5GB", a
quotient it computed from a total the prompt had supplied.  Instructing
a model not to use a number it can see is a request.  Not showing it one
is a constraint.

**The rule was stated three ways here and the three disagreed**, which
is what ``SNAG-DOCS-004`` was about.  Two of the disagreements were real
and each has a right side, so this module is the union of the three
rather than the intersection:

1. **The instruction half is out of scope, and only one of the three
   said so.**  Every ``REVIEW_INSTRUCTIONS`` block numbers its sections
   ("1) … 2) … 3) …") and caps the model at 150 words.  Those digits are
   instructions *to* the model, not measurements *about* the box — there
   is nothing for the model to restate about the week in them, and no
   live generation has ever restated either.  So the claim was always
   about the data half; two docstrings said "contains no digit by
   construction" until 2026-08-25 and were false in a half the rule
   never covered.

2. **An API path may carry a digit and must survive**, which the disk
   and log tests knew and the health one did not.  An executor like
   ``POST /api/files/clean/downloads`` is a string the model has to be
   able to quote back verbatim, so it is stripped before the digit test
   rather than being allowed to fail it.  Measured 2026-08-25 the strip
   is a **no-op on all three fixtures** — one data half contains a path
   at all and that path is digit-free — so it is policy, not a patch:
   the day a route is versioned, ``/api/v2/…`` is not a leak.

3. **A boundary that cannot be found is not a half**, which the health
   test knew and the other two did not.  ``prompt.split(instructions)[0]``
   returns the *whole prompt* when the instruction block is absent, so
   the digit test would go on passing against a prompt that had quietly
   stopped carrying instructions.  It would pass for a stricter reason
   rather than a wrong one — but a helper that silently returns
   something other than what its name says is ``ports_checked``'s rule
   one directory over, where zero-because-clean must not be served as
   zero-because-blind.  :func:`data_half` asserts the marker instead.

This lives in ``tests/`` and not beside the modules because it is a
property of what the three prompts may contain, asserted by tests, and
nothing in production reads it.  It is a plain module rather than an
addition to ``conftest.py`` because it is not a fixture and is wanted by
three modules rather than by the suite — ``conftest`` owns the app, the
database session and ``services.yaml``, which every test needs.
"""

import re

#: An executor path the model must be able to quote back.  See rule 2 in
#: the module docstring for why a digit inside one is not a leak.
_API_PATH = re.compile(r"/api/\S+")

_DIGIT = re.compile(r"\d")


def data_half(prompt: str, instructions: str) -> str:
    """The part of ``prompt`` built from the data, before ``instructions``.

    Asserts the boundary exists rather than falling back to the whole
    prompt — see rule 3 in the module docstring.  Returns the head
    verbatim, API paths and all: stripping them here would make the
    function lie about what it returned, and the strip belongs to the
    digit assertion that wants it.
    """
    head, marker, _ = prompt.partition(instructions)
    assert marker, "the instruction block must be present and separable"
    return head


def assert_no_figure_reaches_the_model(prompt: str, instructions: str) -> None:
    """Rule 2, in the narrow form that is true of all three modules.

    Line by line, so a failure names the line that leaked rather than
    handing the reader a whole prompt to search.

    The strip runs to the next whitespace, so a figure carried *inside*
    a path — ``/api/logs/recent?hours=24``, and routes here do take
    query strings — would be swallowed with it.  Inherited from the two
    copies this replaces and left as it was, on a measurement rather
    than on the assumption that made the first draft of this paragraph
    say no route took one: the executors that reach a prompt are
    hand-written literals in ``files/recommendations.py``, every one a
    bare path followed by a space, and the only one any of the three
    live fixtures emits is ``POST /api/files/clean/downloads``.
    """
    for line in data_half(prompt, instructions).splitlines():
        stripped = _API_PATH.sub("", line)
        assert not _DIGIT.search(stripped), f"figure leaked into prompt: {line!r}"


def assert_the_digits_are_in_the_instructions(instructions: str) -> None:
    """The other half of the same claim, stated rather than implied.

    A reader checking any of the three docstrings against the prompt it
    describes will find digits, so the reason has to be recorded where
    they look.  Without this, the narrow claim above reads as though the
    prompt had no digits anywhere and the next reader either weakens the
    rule or adds a filter the instruction block does not need.
    """
    assert _DIGIT.search(instructions), "the section numbers and word cap are digits"
