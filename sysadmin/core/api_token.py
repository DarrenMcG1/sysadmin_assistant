"""Where the API's bearer token comes from — ``SNAG-API-005``'s token half.

``config.yaml`` is committed and this repository is public (ADR-0010), so
a token written under ``api.auth_token`` is published. The token is a
systemd credential instead, delivered the way ADR-0003 delivers the broker
password: ``LoadCredential=api-token:/etc/credstore/sysadmin-api-token``
on ``sysadmin.service``, read by systemd as root and exposed to the daemon
as ``$CREDENTIALS_DIRECTORY/api-token``.

**The tray reads the copy systemd delivered, never the source.** The
delivered directory carries an ACL for the service user, so the tray (a
user unit, the same user) can read it while the daemon runs, and the two
cannot hold different tokens: what the tray sends is byte for byte what
the daemon loaded at its last start. A source file in the home directory
would let a rotation without a restart split them.

**What the token stops, stated so it is not over-read.** A process under
another uid — ``postgres``, ``mosquitto``, ``libvirt-qemu``, ``nobody`` —
cannot read the delivered copy and is refused. A process running as the
service user can read it exactly as the tray does, so the token is no
boundary against that user's own processes; no design in which the tray
holds the token could be.

Stdlib only, because the tray imports it.
"""

from __future__ import annotations

import os
from pathlib import Path

#: The variable systemd sets for ``LoadCredential=``. Not a setting: the
#: no-environment-variables rule is about where settings live (ADR-0003).
CREDENTIALS_ENV = "CREDENTIALS_DIRECTORY"

#: The ``LoadCredential=`` id on ``sysadmin.service``. A constant rather
#: than a config key: the unit file pins it, and an operator who changed
#: it in ``config.yaml`` alone would turn auth off without a word.
CREDENTIAL_ID = "api-token"

#: Where systemd delivers ``sysadmin.service``'s credentials — the
#: documented ``/run/credentials/<unit>`` — read by the tray.
DELIVERED_DIRECTORY = Path("/run/credentials/sysadmin.service")


def read_token(path: Path) -> str | None:
    """The token in ``path``, stripped, or ``None`` if absent, unreadable or blank."""
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return token or None


def daemon_token() -> str | None:
    """``$CREDENTIALS_DIRECTORY/api-token``, or ``None`` outside the unit."""
    directory = os.environ.get(CREDENTIALS_ENV)
    if not directory:
        return None
    return read_token(Path(directory) / CREDENTIAL_ID)


def tray_token() -> str | None:
    """The daemon's delivered copy, or ``None`` while the daemon is down."""
    return read_token(DELIVERED_DIRECTORY / CREDENTIAL_ID)
