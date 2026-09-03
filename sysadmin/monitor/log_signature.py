"""Turn a log message into a stable identity for one recurring fault.

``SNAG-AGENT-005``: the log aggregator raised **one alert row per matching
log entry**, which is how 593,814 unresolved rows accumulated under
``agent='log_aggregator'`` — 91 % of every unresolved alert in the table.
The fix is a *raise* rule rather than a resolve rule, because a log line
that was written cannot un-write itself: there is no run at which "this
would not be raised" becomes true, which is the question
:meth:`sysadmin.monitor.agent.SysAdminAgent._resolve_recovered` asks of a
*state*.

Deduplicating needs an identity, and the alert title was the wrong one.
``Log error: kernel`` is shared by every kernel error whatever it says, so
plain dedup would have let the Bluetooth firmware storm hold the single
open row while an RCU stall and a USB enumeration failure — both present
in the same 30-day window — went silent.  Trading half a million rows for
a mask over every other kernel fault is not a fix.

So the identity is the message with its **variable parts removed**.
Measured against the live 30-day kernel population, which is the only
reason to believe these rules are the right ones:

===================================================  =======  ===========
Message                                              Rows     Signatures
===================================================  =======  ===========
``Bluetooth: hci0: Failed to set up firmware (-2)``  297,390  1
``Bluetooth: hci0: Failed to load firmware…``        297,389  1
``usb 1-11: device …, error -110 / -71`` (3 forms)   110      2
``rcu:``/``INFO: task …`` hang reports               8        2
===================================================  =======  ===========

**Normalisation trades precision for boundedness, and the trade is
deliberate.** ``error -110`` (ETIMEDOUT) and ``error -71`` (EPROTO)
collapse into one signature, which loses a distinction a human might want.
Nothing is actually lost: the alert's ``message`` column carries the last
verbatim line, so the exact errno is one click away, and
``details['occurrences']`` carries the count that used to be expressed as
row volume.  The signature exists to bound the table, not to diagnose.
"""

import hashlib
import re

from sysadmin.core.text import TRUNCATION_MARKER, truncate_at_word

__all__ = [
    "SIGNATURE_DIGEST_CHARS",
    "TITLE_MAX",
    "alert_title",
    "signature",
    "signature_digest",
]

#: ``sysadmin.alerts.title`` is ``String(255)``.  A title assembled past
#: that raises ``StringDataRightTruncation``, so the budget is computed
#: from the column rather than guessed.
TITLE_MAX = 255

# Hex first: 0x1f would otherwise become 0xNf, which is a different
# signature for every address rather than one for all of them.
_HEX = re.compile(r"\b0x[0-9a-fA-F]+\b")
_NUM = re.compile(r"\d+")
_WS = re.compile(r"\s+")


def signature(message: str) -> str:
    """Reduce ``message`` to the fault it reports, dropping the specifics.

    Digit runs become ``N`` and hex literals ``0xN``, so a device index, a
    PID, an errno and a kernel version all stop forking the identity;
    whitespace is collapsed because the kernel indents continuation lines
    with tabs and a signature must not depend on layout.
    """
    return _WS.sub(" ", _NUM.sub("N", _HEX.sub("0xN", message))).strip()


#: How many hex characters of the full signature's digest a **cut**
#: render carries — a title here, and since 2026-09-03 a member line
#: and an advice title in :mod:`sysadmin.monitor.log_actions`.
#:
#: Eight is the smallest width at which the discriminator is not itself a
#: source of collisions at any volume this table can reach: 32 bits over
#: the 50 distinct signatures live here, or over the 44 the whole kernel
#: population collapses to, puts the birthday probability under 3e-7.  It
#: is a **width**, not a threshold — nothing sits near it and nothing has
#: to be re-measured when the population grows by an order of magnitude.
SIGNATURE_DIGEST_CHARS = 8


def signature_digest(signature_text: str) -> str:
    """A stable discriminator for a signature a render cannot hold whole.

    ``hashlib`` rather than the builtin :func:`hash`, and the reason is
    not style: ``hash()`` is salted per process by ``PYTHONHASHSEED``, so
    the aggregator writing a row and :func:`sysadmin.monitor.log_trends`
    computing the same title for :attr:`SignatureTrend.alert_title` — two
    processes, or one process either side of a restart — would disagree
    about the identity of one fault.  That is the defect this suffix
    exists to remove, arriving through its own fix.

    **Public since 2026-09-03 because a second render needed the same
    eight characters, not eight of its own** (``SNAG-LOG-013``).
    :func:`~sysadmin.monitor.log_actions.capped_signature` cuts the same
    signature at a smaller bound for the advice surface, and the whole
    value of stamping it there is that a reader can carry
    ``[a028de53]`` from a roll-up's member line to the alert row for the
    same fault and find it again.  A second ``sha256(...)[:8]`` written
    beside this one is two statements of one identity free to drift —
    ``SNAG-DB-003``'s shape, and :func:`sysadmin.core.journal.max_priority_for`
    against ``PRIORITY_MAP``'s rule.

    Both callers digest the **whole** signature and never the cut they
    are about to emit: a digest of the surviving prefix is by
    construction *identical* across exactly the pairs it exists to
    separate, so it would discriminate nothing while looking as though
    it did.
    """
    return hashlib.sha256(signature_text.encode("utf-8")).hexdigest()[:SIGNATURE_DIGEST_CHARS]


def alert_title(severity: str, source: str, message: str) -> str:
    """Build the deduplication key, which is also what the reader sees.

    The signature lives **in the title** rather than in ``details`` for two
    reasons.  Dedup, the set-based resolve and the tray's
    ``{severity}:{title}`` fingerprint all key on title already, so no new
    machinery is needed and none of them can disagree about identity.  And
    ``Log error: kernel`` told a reader nothing at all — four open rows
    with that text are indistinguishable on the tray, which is the state
    this snag leaves behind if the key is hidden in JSONB.

    The signature is truncated with :func:`~sysadmin.core.text.truncate_at_word`
    and the budget accounts for the marker, because that helper may exceed
    its own limit by the marker's length (deliberately — see
    ``SNAG-BRIEF-002``) and this one lands in a ``String(255)`` column.

    **A cut identity is not an identity, and the marked cut was hiding
    that rather than saying it** (``SNAG-LOG-013``, whose stated scope
    this is outside).  That entry prices its cost at *"a GET advice
    surface, no toast and no row"*; the same defeat lands here, where the
    title **is** the dedup key, so two faults agreeing past the budget
    share one row, one fingerprint and one toast — ``SNAG-AGENT-005``'s
    masking defect at the surface that entry exists to protect, arriving
    from the other side.  Measured on the population that entry itself
    observed, recovered from ``raw_line`` because ``SNAG-LOG-008``'s
    backfill has since rewritten ``message``: **39 distinct signatures
    collapse to 21 titles, four of which cover 2, 2, 2 and 16 distinct
    faults**.  The sixteen are ``warning`` and so stored rather than
    raised; one of the pairs is ``error`` and did raise.

    So a cut title carries :func:`signature_digest` of the **whole**
    signature.
    Three things decided that shape:

    1. **Only a cut title carries one.**  An uncut signature is already
       total, and stamping every title would move every open row's
       fingerprint at the deploy for no gain — the mass re-raise
       ``escalation.step_for`` refuses one row at a time.
    2. **The digest is of the signature, never of the message.**  Several
       messages share one signature by design (that is the whole of
       :func:`signature`), so digesting the message would fork the
       identity per errno and rebuild the 598,091 rows.
    3. **It restores totality rather than making a collision unlikely.**
       Raising ``TITLE_MAX`` moves where the cut falls and nothing else,
       which is ``SNAG-LOG-013``'s own argument against raising a cap;
       a discriminator computed over the part that was cut away is the
       only per-row pure function that cannot be defeated by two records
       differing past the bound.

    The live margin is why this is not merely hygiene.  Two of the 50
    signatures on this box are cut at all and neither collides, but the
    surviving one is a Python traceback whose first 211 characters are
    starlette's ``lifespan`` frame — boilerplate shared by *every*
    lifespan-time failure, which is the class ``schema_guard`` raises.
    The population needs one second startup fault and nothing else.
    """
    prefix = f"Log {severity}: {source} — "
    budget = TITLE_MAX - len(prefix) - len(TRUNCATION_MARKER) - 1
    text = signature(message)
    if len(text) <= budget:
        return f"{prefix}{text}"
    suffix = f" [{signature_digest(text)}]"
    cut = truncate_at_word(text, max(budget - len(suffix), 1))
    return f"{prefix}{cut}{suffix}"
