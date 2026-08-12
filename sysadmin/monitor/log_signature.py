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

import re

from sysadmin.core.text import TRUNCATION_MARKER, truncate_at_word

__all__ = ["TITLE_MAX", "alert_title", "signature"]

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
    """
    prefix = f"Log {severity}: {source} — "
    budget = TITLE_MAX - len(prefix) - len(TRUNCATION_MARKER) - 1
    return f"{prefix}{truncate_at_word(signature(message), max(budget, 1))}"
