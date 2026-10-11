"""Alfred's Telegram bot, watched from the day it exists.

Estate message ``d01b0798`` (alfred, 2026-10-11) announced that Alfred's
``GET /api/health`` gains a ``telegram`` field — ``ok``, ``degraded`` or
``disabled`` (their ADR-0139 §8) — and left whether to watch it to this
repository. **Watched, but not yet**, and this file is what makes "not
yet" end on its own.

**Why no entry today.** The field reads ``disabled`` until the owner
creates the bot, and was absent from the live body when this was written
(their commit follows the announcement). ``expect: {path: telegram,
equals: ok}`` would therefore be ``unevaluable`` and then ``unmet`` from
its first poll: an alert about a state the owner chose. A ``mute: true``
entry was rejected for the reason a note in ``tasks.md`` would be — it
ends only when someone remembers to unmute it.

**The gate is the credential file, not the body.** ADR-0139's amendment
puts the prod token in ``~/.config/alfred/telegram.env``, read by
``alfred-backend.service``'s ``EnvironmentFile=`` — "no file, no
polling". The file is installed once and stays; the body's ``telegram``
value is the very thing that flips when the bot is in trouble, so a
gate keyed on it would close exactly when the check is needed
(``test_searxng_wiring``'s rule: a unit file, never a live probe).

**The shape asserted is ``alfred-bus``'s**, by the reasoning the owner
ruled for that entry on 2026-09-25: the bot is non-critical (an outage
never takes the backend down, their ADR-0139 §2), so its faults go on
their own entry and never charge the ``alfred`` entry's reliability
score. ``equals: ok`` is strict for the same reason ``bus``'s is — once
the token file exists, ``disabled`` means the unit is not reading it,
which is a fault and not a choice.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

#: Where ADR-0139 puts prod's token. Its existence is the owner having
#: created the bot.
TOKEN_FILE = Path.home() / ".config/alfred/telegram.env"

SERVICES_YAML = Path(__file__).resolve().parents[1] / "services.yaml"


def _bot_configured() -> bool:
    return TOKEN_FILE.exists()


def _telegram_entries() -> list[dict]:
    """Alfred entries whose ``expect:`` reads the ``telegram`` field."""
    services = yaml.safe_load(SERVICES_YAML.read_text())["services"]
    return [
        s
        for s in services
        if s.get("project") == "alfred"
        and (s.get("expect") or {}).get("path") == "telegram"
    ]


@pytest.mark.skipif(
    not _bot_configured(),
    reason="no ~/.config/alfred/telegram.env — the owner has not created "
    "Alfred's Telegram bot yet",
)
def test_alfred_telegram_is_watched_on_its_own_entry():
    """A configured bot that nothing reads is the gap."""
    entries = [e for e in _telegram_entries() if e.get("monitor", True)]

    assert len(entries) == 1, (
        f"{TOKEN_FILE} exists, so Alfred's Telegram bot is configured, and "
        f"{len(entries)} monitored services.yaml entries read its health. "
        "Declare `alfred-telegram` beside `alfred-bus`, in the same shape: "
        "kind: http, url http://localhost:8100/api/health, "
        "expect: { path: telegram, equals: ok }, no port and no systemd "
        "(both held by the `alfred` entry). Estate message d01b0798."
    )
    entry = entries[0]
    assert entry.get("name") != "alfred", (
        "the telegram condition sits on the `alfred` entry, so a Telegram "
        "outage would charge the backend's reliability score; the owner "
        "ruled against that shape for `bus` on 2026-09-25 and the bot is "
        "non-critical by the same reasoning (Alfred ADR-0139 §2)."
    )
    assert entry["expect"].get("equals") == "ok", (
        "the condition must be strict: with the token file present, "
        "`disabled` means the unit is not reading it, which is a fault."
    )


# --------------------------------------------------------------------------
# The gate itself
# --------------------------------------------------------------------------
#
# The test above skips everywhere until the owner creates the bot, which
# makes it unfalsifiable on its own: a gate that has never fired and one
# that cannot fire look the same. These drive the gate against a path
# the test controls, so they run in CI and on this box alike.


@pytest.fixture
def fake_token(tmp_path, monkeypatch):
    path = tmp_path / "telegram.env"
    monkeypatch.setattr("tests.test_alfred_telegram_wiring.TOKEN_FILE", path)
    return path


def test_gate_is_closed_without_the_token_file(fake_token):
    assert not _bot_configured()


def test_gate_opens_when_the_token_file_is_installed(fake_token):
    fake_token.write_text("ALFRED_TELEGRAM_BOT_TOKEN=x\n")
    assert _bot_configured()

