"""Services tab — compose-like service cards with status, PID, memory, actions.

Each monitored service gets a card showing its systemd state, resource usage,
and action buttons for restart/start/stop.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sysadmin_tray.models import ServiceDetailInfo, ServiceStatus, StatusResponse
from sysadmin_tray.styles import (
    BG_CARD,
    BG_PRIMARY,
    BORDER,
    BUTTON_STYLE,
    GREEN,
    GREY,
    RED,
    STATUS_COLOURS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

if TYPE_CHECKING:
    from sysadmin_tray.client import ApiClient

logger = logging.getLogger(__name__)


def _format_memory(bytes_val: int) -> str:
    """Format memory bytes into a human-readable string."""
    if bytes_val <= 0:
        return "\u2014"
    mb = bytes_val / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB"


class ServiceCard(QFrame):
    """A card representing a single monitored service.

    Shows status dot, service name, systemd state, port, PID, memory,
    and action buttons.
    """

    def __init__(
        self,
        service: ServiceStatus,
        client: ApiClient,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._client = client
        self._action_pending = False

        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
        """)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # ── Top row: status dot + name + state ───────────────
        top = QHBoxLayout()

        self._dot = QLabel("\u2b24")
        self._dot.setFixedWidth(18)
        self._dot.setStyleSheet(f"font-size: 12px; color: {GREY};")
        top.addWidget(self._dot)

        self._name_label = QLabel(self._service.name)
        self._name_label.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};"
        )
        top.addWidget(self._name_label)

        top.addStretch()

        self._state_label = QLabel("")
        self._state_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        top.addWidget(self._state_label)

        layout.addLayout(top)

        # ── Detail row: port, PID, memory ────────────────────
        self._detail_label = QLabel("")
        self._detail_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        layout.addWidget(self._detail_label)

        # ── Action buttons ───────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._restart_btn = QPushButton("Restart")
        self._restart_btn.setStyleSheet(BUTTON_STYLE)
        self._restart_btn.setFixedWidth(80)
        self._restart_btn.clicked.connect(lambda: self._do_action("restart"))

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setStyleSheet(BUTTON_STYLE)
        self._stop_btn.setFixedWidth(80)
        self._stop_btn.clicked.connect(lambda: self._do_action("stop"))

        self._start_btn = QPushButton("Start")
        self._start_btn.setStyleSheet(BUTTON_STYLE)
        self._start_btn.setFixedWidth(80)
        self._start_btn.clicked.connect(lambda: self._do_action("start"))

        btn_row.addWidget(self._restart_btn)
        btn_row.addWidget(self._stop_btn)
        btn_row.addWidget(self._start_btn)

        layout.addLayout(btn_row)

        # Initial state
        self.update_status(self._service)

    def update_status(self, service: ServiceStatus) -> None:
        """Update from a StatusResponse service entry."""
        self._service = service
        colour = STATUS_COLOURS.get(service.status, GREY)
        self._dot.setStyleSheet(f"font-size: 12px; color: {colour};")

        has_unit = bool(service.systemd_unit)
        can_control = has_unit and service.controllable
        self._restart_btn.setVisible(can_control)
        self._stop_btn.setVisible(can_control and service.status == "ok")
        self._start_btn.setVisible(can_control and service.status != "ok")

    def update_details(self, detail: ServiceDetailInfo) -> None:
        """Update from a ServiceDetailInfo (systemd unit details)."""
        state_text = f"{detail.active_state} ({detail.sub_state})"
        self._state_label.setText(state_text)

        parts = []
        if detail.main_pid > 0:
            parts.append(f"PID: {detail.main_pid}")
        if detail.memory_current > 0:
            parts.append(f"Memory: {_format_memory(detail.memory_current)}")
        self._detail_label.setText("  \u00b7  ".join(parts) if parts else "")

        # Update dot colour based on active state
        if detail.is_active:
            self._dot.setStyleSheet(f"font-size: 12px; color: {GREEN};")
        else:
            self._dot.setStyleSheet(f"font-size: 12px; color: {RED};")

    def _do_action(self, action: str) -> None:
        """Trigger a service action and disable buttons meanwhile."""
        if self._action_pending:
            return
        self._action_pending = True
        self._restart_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)
        self._start_btn.setEnabled(False)
        self._client.trigger_service_action(self._service.name, action)

    def on_action_complete(
        self, service_name: str, action: str, success: bool, message: str
    ) -> None:
        """Re-enable buttons after an action completes."""
        if service_name != self._service.name:
            return
        self._action_pending = False
        self._restart_btn.setEnabled(True)
        self._stop_btn.setEnabled(True)
        self._start_btn.setEnabled(True)

    @property
    def service_name(self) -> str:
        return self._service.name

    @property
    def has_systemd_unit(self) -> bool:
        """Whether ``/details`` has anything to say about this service.

        Read off the card's *current* status rather than the one it was
        built from, so a service that gains or loses a unit declaration
        across a ``services.yaml`` reload is answered correctly without the
        card being rebuilt.  It is the same test ``update_status`` uses to
        decide whether the lifecycle buttons are shown.
        """
        return bool(self._service.systemd_unit)


class ServicesTab(QWidget):
    """Dashboard tab displaying service cards with lifecycle controls."""

    def __init__(self, client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client
        self._cards: dict[str, ServiceCard] = {}
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ── Header row ───────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("Services")
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        self._scan_btn = QPushButton("Scan All")
        self._scan_btn.setStyleSheet(BUTTON_STYLE)
        self._scan_btn.clicked.connect(self._on_scan)
        header.addWidget(self._scan_btn)
        layout.addLayout(header)

        # ── Scrollable card area ─────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background-color: {BG_PRIMARY};")

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_container)
        layout.addWidget(scroll)

    def _connect_signals(self) -> None:
        self._client.status_updated.connect(self._on_status)
        self._client.service_detail_updated.connect(self._on_detail)
        self._client.service_action_complete.connect(self._on_action_complete)
        self._client.scan_complete.connect(self._on_scan_complete)

    def _on_status(self, status: StatusResponse) -> None:
        """Create/update service cards from the status response.

        The cards themselves are always updated — they are in memory and
        the window may be shown at any moment — but the per-service
        ``/details`` fan-out is gated on this tab being visible.  See
        :meth:`_fetch_details` for why.
        """
        seen: set[str] = set()
        visible = self.isVisible()

        for svc in status.services:
            seen.add(svc.name)
            if svc.name not in self._cards:
                card = ServiceCard(svc, self._client)
                self._cards[svc.name] = card
                # Insert before the stretch
                self._cards_layout.insertWidget(
                    self._cards_layout.count() - 1, card
                )
            else:
                self._cards[svc.name].update_status(svc)

            # Request details for services with systemd units — but only
            # while something is actually looking at them.  See
            # :meth:`_fetch_details`.
            if visible and svc.systemd_unit:
                self._client.request_service_details(svc.name)

        # Remove cards for services no longer present
        for name in list(self._cards):
            if name not in seen:
                card = self._cards.pop(name)
                self._cards_layout.removeWidget(card)
                card.deleteLater()

    def _on_detail(self, service_name: str, detail: ServiceDetailInfo) -> None:
        """Update a card with detailed systemd info."""
        if service_name in self._cards:
            self._cards[service_name].update_details(detail)

    def _on_action_complete(
        self, service_name: str, action: str, success: bool, message: str
    ) -> None:
        """Forward action completion to the relevant card."""
        if service_name in self._cards:
            self._cards[service_name].on_action_complete(
                service_name, action, success, message
            )
        # Re-fetch status after action
        if success:
            self._client.request_status()

    def _on_scan(self) -> None:
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Scanning\u2026")
        self._client.trigger_scan()

    def _on_scan_complete(self, success: bool, message: str) -> None:
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("Scan All")

    def refresh(self) -> None:
        """Called when this tab becomes visible — fetch what it shows.

        Both halves are needed and they cover different cases.  The status
        request covers a cold tab, where there are no cards yet: the reply
        arrives with this tab already visible, so :meth:`_on_status` fans
        the details out itself.  :meth:`_fetch_details` covers a warm one,
        where cards were built from status polls taken while the window was
        hidden and carry no systemd detail — without it those cards would
        sit blank until the next poll, up to ``tray.status_poll_seconds``
        later, which is the visible cost of the gate and the reason it is
        paid here rather than by widening the gate.
        """
        self._client.request_status()
        self._fetch_details()

    def _fetch_details(self) -> None:
        """Request ``/details`` for every card holding a systemd unit.

        **SNAG-AGENT-008, volume half.** This tab is constructed eagerly at
        tray startup and wired to ``status_updated`` unconditionally, so it
        used to issue one ``/details`` request per service on every status
        poll whether or not the dashboard had ever been opened — 32
        services every ``tray.status_poll_seconds``.  Measured 2026-08-17:
        1,160 of the 1,347 journal lines ``sysadmin.service`` wrote in ten
        minutes, **86 %**, were that fan-out answering itself.

        ``DashboardWindow``'s own docstring already promised the opposite —
        *"no background polling when hidden"* — and every other tab keeps
        it; ``LogsTab`` stops its timer in ``hideEvent`` and this one had
        no timer to stop, which is how it escaped notice.  The polling was
        not scheduled here, it was inherited from a signal that fires
        anyway.

        ``isVisible()`` is false both when the window is hidden and when a
        different tab is selected, and both are cases where nobody is
        looking — so the widget's own answer is the right one and no
        separate flag is kept.  A second flag would be a second statement
        of the same fact, free to disagree with Qt about it.
        """
        for name, card in self._cards.items():
            if card.has_systemd_unit:
                self._client.request_service_details(name)
