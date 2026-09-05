"""Session 14 — shared defaults and config-lifted magic numbers.

Guards against the backend and tray drifting apart on host/port, and
pins the defaults for values that used to be hard-coded in routers/main.

Since 2026-08-28 it also holds the *shipped-file* half of that drift
question: the reminder ceiling ``SNAG-ESTATE-009`` now rests on, and the
two ``reminder_hours`` leaves whose agreement was held by a comment.
"""

from pathlib import Path

import pytest
import yaml

from sysadmin.core.config import (
    AppConfig,
    FileOrganiserConfig,
    HealthGradeBands,
    SchedulesConfig,
    ServiceConfig,
    get_config,
    load_config,
    parse_config,
)
from sysadmin.core.defaults import DEFAULT_API_HOST, DEFAULT_API_PORT, default_api_url
from sysadmin.monitor.services import ServiceEntry
from sysadmin.snag_claims import REPO_ROOT, REVIEW_SCHEDULE_LEAVES, attribute_reads
from sysadmin_tray.config import TrayConfig, load_tray_config


class TestSharedDefaults:
    def test_backend_service_config_uses_shared_defaults(self):
        svc = ServiceConfig()
        assert svc.host == DEFAULT_API_HOST
        assert svc.port == DEFAULT_API_PORT

    def test_tray_default_api_url_matches_shared_defaults(self):
        assert TrayConfig().api_url == default_api_url()
        assert TrayConfig().api_url == f"http://{DEFAULT_API_HOST}:{DEFAULT_API_PORT}"

    def test_tray_fallback_without_config_file_uses_shared_defaults(self, tmp_path):
        cfg = load_tray_config(config_path=tmp_path / "missing.yaml")
        assert cfg.api_url == default_api_url()

    def test_default_api_url_formats_overrides(self):
        assert default_api_url("192.168.1.10", 9000) == "http://192.168.1.10:9000"


class TestLiftedMagicNumbers:
    def test_grade_bands_defaults(self):
        bands = HealthGradeBands()
        assert (bands.healthy_min, bands.needs_attention_min, bands.neglected_min) == (
            80,
            60,
            40,
        )

    def test_reclaimable_milestones_default(self):
        assert FileOrganiserConfig().reclaimable_milestones_mb == [1024, 5120, 10240]

    def test_schedules_defaults(self):
        s = SchedulesConfig()
        assert (s.briefing_hour, s.briefing_minute) == (6, 0)
        assert (s.retention_hour, s.retention_minute) == (3, 0)

    def test_cors_origins_default(self):
        assert ServiceConfig().cors_origins == [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    def test_app_config_exposes_new_sections(self):
        cfg = AppConfig()
        assert cfg.schedules.briefing_hour == 6
        assert cfg.agents.project_organiser.grade_bands.healthy_min == 80
        assert cfg.agents.file_organiser.reclaimable_milestones_mb[0] == 1024


class TestServiceMute:
    """Session 16 — per-service mute flag for expected-down services.

    Moved to services.yaml with the rest of the topology. Every service
    can now carry it, which was not true while half of them were
    generated from projects.yaml with no flag of their own.
    """

    def test_mute_defaults_to_false(self):
        svc = ServiceEntry(name="redis", kind="tcp", host="h", port=6379)
        assert svc.mute is False

    def test_mute_can_be_set(self):
        svc = ServiceEntry(name="redis", kind="tcp", host="h", port=6379, mute=True)
        assert svc.mute is True


class TestSession17Defaults:
    """Self-monitoring, SSE, and anomaly-detection tunables."""

    def test_self_monitor_defaults(self):
        cfg = AppConfig().self_monitor
        assert cfg.enabled is True
        assert cfg.stall_grace_multiplier == 3.0
        assert cfg.min_stall_grace_seconds == 300
        assert cfg.recent_runs == 10

    def test_events_defaults(self):
        cfg = AppConfig().events
        assert cfg.heartbeat_seconds == 20.0
        assert cfg.max_queued_events == 100
        assert cfg.retry_ms == 5000

    def test_anomaly_defaults(self):
        cfg = AppConfig().agents.sysadmin.anomaly
        assert cfg.enabled is True
        assert cfg.window_days == 7
        assert cfg.z_threshold == 3.0
        assert cfg.min_samples == 30
        assert cfg.min_stdev == 1.0
        assert cfg.severity == "warning"

    def test_repo_config_yaml_declares_the_new_sections(self):
        """The committed config.yaml must still validate with the new blocks."""
        from pathlib import Path

        import yaml

        raw = yaml.safe_load(
            (Path(__file__).parent.parent / "config.yaml").read_text()
        )
        cfg = AppConfig.model_validate(raw)

        assert cfg.self_monitor.stall_grace_multiplier == 3.0
        assert cfg.events.heartbeat_seconds == 20
        assert cfg.agents.sysadmin.anomaly.z_threshold == 3.0


class TestSession18Defaults:
    """File-action settings and the interval-job first-run delay."""

    def test_file_actions_defaults(self):
        cfg = AppConfig().agents.file_organiser.actions
        assert cfg.enabled is True
        assert cfg.downloads_dir == "Downloads"
        assert cfg.archive_dir == "Archives/Downloads"
        assert cfg.duplicate_strategy == "newest"
        assert cfg.pdf_book_min_pages == 50
        assert cfg.max_operations == 200
        # Permanent deletion is opt-in — trashing is the default
        assert cfg.allow_permanent_delete is False
        assert cfg.trash_dir is None

    def test_default_category_folders(self):
        folders = AppConfig().agents.file_organiser.actions.category_folders
        assert folders == {
            "images": "Pictures",
            "videos": "Videos",
            "documents": "Documents",
            "audio": "Music",
            "books": "Books",
            "archives": "Archives",
        }

    def test_category_mapping_is_config_driven(self):
        """Retargeting a category needs no code change."""
        cfg = FileOrganiserConfig.model_validate(
            {"actions": {"category_folders": {"images": "Media/Photos"}}}
        )
        assert cfg.actions.category_folders["images"] == "Media/Photos"

    def test_agent_first_run_delay_default(self):
        assert SchedulesConfig().agent_first_run_delay_seconds == 60

    def test_repo_config_yaml_declares_the_action_settings(self):
        from pathlib import Path

        import yaml

        raw = yaml.safe_load(
            (Path(__file__).parent.parent / "config.yaml").read_text()
        )
        cfg = AppConfig.model_validate(raw)

        actions = cfg.agents.file_organiser.actions
        assert actions.enabled is True
        assert actions.allow_permanent_delete is False
        assert actions.category_folders["books"] == "Books"
        assert actions.category_folders["archives"] == "Archives"
        assert ".py" in actions.code_extensions
        assert cfg.schedules.agent_first_run_delay_seconds == 60


# ── The reminder ceiling (SNAG-ESTATE-009) ───────────────────────────────
#
# Session 117 bounded that entry's loud rung by *arithmetic* rather than by
# luck: a dev server's port is unattributed until the next unit sweep, and
# the estate judge quietens it to ``info`` on its first poll after that
# sweep.  So the worst case is one sweep interval plus one poll interval —
# 6 + 1 = 7 h on this box — against a ``reminder_hours`` of 24, and the
# repeat that used to restate the fault at ``warning`` for a day and a half
# is unreachable.  Nothing protected that inequality until this class.

REPO_CONFIG = Path(__file__).parent.parent / "config.yaml"

#: Index of ``notifications.tray.reminder_hours`` among the file's two
#: ``reminder_hours:`` leaves — the understudy's copy is 0 and comes
#: first.  Positional, and therefore itself a mutable fact: every caller
#: reads the result back through the real parser and asserts the leaf it
#: meant to move is the one that moved.  No constant is defined for the
#: understudy, because nothing targets it — a name nothing passes is
#: ``SNAG-CFG-001`` at the size of a constant.
TRAY = 1


def _with_reminder_hours(destination: Path, which: int, value: float) -> Path:
    """Copy the shipped config with one ``reminder_hours:`` leaf rewritten.

    Located by **position and key**, then rewritten wholesale — never by
    replacing the string ``"24"``.  A fixture that edits the current value
    matches nothing the day that value moves and then tests whatever the
    file happened to say, which is how the first draft of this class went
    red under an unrelated mutation: *"a probe keys on identity, not a
    mutable field"*, met inside the guard written for it.

    ``which`` is a position, so this function is not trusted on its own:
    each caller asserts through ``load_tray_config`` / ``load_config``
    that the leaf it named is the leaf that moved, which is the witness
    a reordering of the ``notifications:`` blocks would fail.
    """
    lines = REPO_CONFIG.read_text().splitlines()
    hits = [
        i
        for i, line in enumerate(lines)
        if line.strip().startswith("reminder_hours:")
    ]
    assert len(hits) == 2, f"expected two reminder_hours leaves, found {len(hits)}"

    line = lines[hits[which]]
    lines[hits[which]] = f"{line[:len(line) - len(line.lstrip())]}reminder_hours: {value}"
    destination.write_text("\n".join(lines) + "\n")
    return destination


def _reminder_ceiling(config_path: Path) -> tuple[int, float] | None:
    """``(loud-rung ceiling in hours, hours until a restatement)``.

    ``None`` when reminders are switched off, which is a *declaration*
    and not a violation: both speakers gate on ``interval <= 0``
    (:meth:`sysadmin.monitor.desktop.DesktopNotifier.sweep_reminders` and
    ``sysadmin_tray.notifications`` alike), so with ``reminder_hours: 0``
    there is no repeat for the ceiling to have to beat and the arithmetic
    has nothing to say.

    The ceiling is **summed from the two intervals, never written as
    7** — ``max_priority_for`` against ``PRIORITY_MAP``'s rule.  A
    literal would be a second statement of an arithmetic ``config.yaml``
    already makes, free to drift from it in exactly the way this guard
    exists to catch.

    The restatement side is read through ``load_tray_config``, the tray's
    own parser, because ``notifications.tray.reminder_hours`` is the leaf
    a repeat is actually due on and
    :class:`~sysadmin.core.config.TrayNotificationsConfig` — the slice the
    *backend* keeps — parses ``mute_services`` alone.  That model is not
    the file: the tray ships in this wheel and reads the same
    ``config.yaml``, so the real leaf is readable here even though no
    backend object holds it.

    **Read with ``parse_config``, which does not install.**
    ``load_config`` is ``set_config(parse_config(...))``, so reading a
    specimen with it left the process-wide ``AppConfig`` holding
    ``scan_interval_hours: 24`` — a configuration this very class exists
    to call incoherent — for every test that ran behind it in the same
    worker.  It was invisible because the class's third test happens to
    reinstall a coherent copy afterwards, and ``pytest-randomly`` makes
    that ordering a per-seed accident rather than a guarantee.  Found by
    ``snag_claims.reload_coherence_reading`` hitting the same trap one
    composition root over, where it made the installed-witness read back
    a value its own helper had written.
    """
    agents = parse_config(config_path).agents
    reminder = load_tray_config(config_path=config_path).reminder_hours
    if reminder <= 0:
        return None
    ceiling = (
        agents.service_discovery.scan_interval_hours
        + agents.estate_judge.poll_interval_hours
    )
    return ceiling, reminder


class TestTheLoudRungEndsBeforeItIsRestated:
    """``SNAG-ESTATE-009``'s ceiling is one config line wide.

    Raising ``agents.service_discovery.scan_interval_hours`` from 6 to 24
    — a plausible edit, since the file organiser already runs daily —
    puts the sum at **25** against a ``reminder_hours`` of 24, and the
    entry's whole re-ranking on 2026-08-28 rests on that sum being under
    it.  The failure is silent: the sweep still runs, the judge still
    quietens, and the only difference is that a dev server's ``warning``
    survives long enough to be restated as though it were news.  The
    family's one recorded episode stood **31.88 h** at ``warning``, which
    is what that looks like.
    """

    def test_the_ceiling_is_under_a_restatement(self):
        measured = _reminder_ceiling(REPO_CONFIG)
        if measured is None:
            # Skipped rather than passed: with reminders off there is no
            # repeat for the ceiling to beat, so the claim is vacuous —
            # and ``ports_checked``'s rule says a check that could not
            # look must not be served as a check that looked and was
            # happy.  A skip is visible in the run; a green is not.
            pytest.skip("notifications.tray.reminder_hours is 0 — reminders off")

        ceiling, reminder = measured
        assert ceiling < reminder, (
            f"a dev server's breach can stay loud for {ceiling} h against a "
            f"reminder_hours of {reminder} h, so SNAG-ESTATE-009's quiet rung "
            f"is restated at warning before it arrives"
        )

    def test_the_detector_moves(self, tmp_path):
        """Driven at a mutation, not asserted about.

        Both terms read ``24`` somewhere on this box already
        (``file_organiser.scan_interval_hours``,
        ``desktop.reminder_hours``), so a guard that merely compared two
        numbers it had found would be green whatever it was reading.
        ``test_autogenerate_config.py``'s idiom — run the detector at
        something that must trip it.
        """
        shipped = _reminder_ceiling(REPO_CONFIG)
        if shipped is None:
            pytest.skip("notifications.tray.reminder_hours is 0 — reminders off")

        before, reminder_hours = shipped
        raw = yaml.safe_load(REPO_CONFIG.read_text())
        raw["agents"]["service_discovery"]["scan_interval_hours"] = int(
            reminder_hours
        )
        mutated = tmp_path / "config.yaml"
        mutated.write_text(yaml.safe_dump(raw))
        ceiling, reminder = _reminder_ceiling(mutated)

        # The *delta*, never the endpoint, and the mutation is built by
        # structure rather than by string.  Three drafts failed here for
        # the same reason: ``ceiling == 25`` is satisfied by a config.yaml
        # already reading 24 and a replacement that matched nothing;
        # ``before == 7`` pins a number the owner may change for unrelated
        # reasons; and a ``replace("scan_interval_hours: 6", …)`` matches
        # nothing the day the sweep is retimed, so a legitimate edit reads
        # as a broken detector.  Setting the interval to ``reminder_hours``
        # violates by construction whatever either leaf currently says.
        assert ceiling > before, "the mutation did not move the sum"
        assert not ceiling < reminder

    def test_reading_a_specimen_does_not_install_it(self, tmp_path):
        """The guard must not leave the process holding what it forbids.

        ``load_config`` installs, so every reading here used to write the
        process-wide slot: after ``test_the_detector_moves`` the singleton
        held ``scan_interval_hours: 24``, which is the configuration this
        class exists to call incoherent, for every test behind it in the
        same worker.  Ten test modules read ``get_config()``, and
        ``pytest-randomly`` decides which of them run after this file.

        Asserted against a **violating** specimen rather than the shipped
        file, because installing the shipped file is invisible — it is
        what the process already holds, so the leak only has a witness
        when the specimen differs.
        """
        shipped = _reminder_ceiling(REPO_CONFIG)
        if shipped is None:
            pytest.skip("notifications.tray.reminder_hours is 0 — reminders off")
        _, reminder_hours = shipped

        raw = yaml.safe_load(REPO_CONFIG.read_text())
        raw["agents"]["service_discovery"]["scan_interval_hours"] = int(reminder_hours)
        specimen = tmp_path / "config.yaml"
        specimen.write_text(yaml.safe_dump(raw))

        before = get_config()
        ceiling, _ = _reminder_ceiling(specimen)

        assert not ceiling < reminder_hours, "the specimen does not violate anything"
        assert get_config() is before, (
            "reading a specimen installed it: the process is now serving a "
            "configuration this class exists to refuse"
        )

    def test_reminders_switched_off_are_not_a_violation(self, tmp_path):
        """``0`` disables the repeat, so there is nothing to be early for.

        Failing here would refuse a configuration both speakers document
        as legitimate, which is a guard that has to be disarmed to be
        obeyed — and a disarmed guard is the ``--no-verify`` shape
        ``check-migrations.sh`` fails open to avoid.
        """
        off = _with_reminder_hours(tmp_path / "config.yaml", TRAY, 0)

        assert load_tray_config(config_path=off).reminder_hours == 0
        assert _reminder_ceiling(off) is None


class TestTheTwoSpeakersAgreeInTheShippedFile:
    """The defaults are pinned; the *file* was not, and only one is edited.

    ``test_desktop_notifier.py::test_the_reminder_interval_matches_the_trays``
    asserts ``DesktopNotificationsConfig().reminder_hours ==
    NotificationSettings().reminder_hours`` — two objects constructed with
    no file, so it holds whatever ``config.yaml`` says.  Driven against a
    copy with the tray's leaf set to 6 and the understudy's left at 24,
    that pin stays green while the two speakers restate the same fault
    four times a day apart: the interval depends on which of them happened
    to be running, which is the one thing the understudy exists to hide.
    """

    def test_the_understudy_carries_the_trays_interval(self):
        tray = load_tray_config(config_path=REPO_CONFIG).reminder_hours
        understudy = load_config(REPO_CONFIG).notifications.desktop.reminder_hours

        assert understudy == tray, (
            f"notifications.desktop.reminder_hours is {understudy} and "
            f"notifications.tray.reminder_hours is {tray}; the daemon and the "
            f"tray would restate one standing fault on two cadences"
        )

    def test_that_claim_is_about_the_file_and_not_the_defaults(self, tmp_path):
        """The witness the defaults pin cannot supply."""
        from sysadmin.core.config import DesktopNotificationsConfig
        from sysadmin_tray.notifications import NotificationSettings

        shipped = load_config(REPO_CONFIG).notifications.desktop.reminder_hours
        skewed = _with_reminder_hours(tmp_path / "config.yaml", TRAY, 6)

        assert load_tray_config(config_path=skewed).reminder_hours == 6
        assert parse_config(skewed).notifications.desktop.reminder_hours == shipped
        assert shipped != 6, "the skew must actually skew the two apart"
        # ...and the existing pin is unmoved by all of it.
        assert (
            DesktopNotificationsConfig().reminder_hours
            == NotificationSettings().reminder_hours
        )


class TestTheSweepIsWhatMakesTheCeilingFinite:
    """The asymmetry: one of the two agents may be switched off harmlessly.

    ``EstateJudgeAgent._attribution`` reads the **newest stored** sweep
    with no age gate — deliberately, so the enrichment never becomes a
    dependency of the alert.  With ``service_discovery`` disabled that
    read freezes, no later sweep ever names a new dev server, and the loud
    rung is bounded by nothing at all: a stronger break of the same
    arithmetic than raising the interval, and invisible to the sum.

    Disabling ``estate_judge`` is the opposite and needs no assertion —
    nothing raises the breach, so there is no loud rung to bound.
    """

    def test_the_sweep_that_supplies_the_quietening_is_scheduled(self):
        agents = load_config(REPO_CONFIG).agents
        assert agents.service_discovery.enabled, (
            "the stored sweep never advances, so a dev server started now is "
            "never attributed and its breach stays loud indefinitely"
        )


class TestTheVacatedReviewLeavesStayGone:
    """``SNAG-CFG-002``'s regression guard, and the half its check could not see.

    ``schedules.review_hour``/``review_minute`` scheduled the weekly
    *project* review.  That review left for estate-manager on 2026-08-13
    (ADR-0005) and the two leaves went on being parsed by pydantic and
    read by nothing until 2026-08-30 — ``SNAG-CFG-001``'s shape at the
    size of two leaves.

    **The retired check could not have witnessed its own closure.**
    ``check_review_schedule_unread`` answered ``match`` whenever it found
    no reader, which is as true of a deleted field as of an unread one —
    a control whose observation does not move across the fix.  So the
    discriminating assertion is the *absence*, and it lives here rather
    than with the detector, because ``SchedulesConfig`` is where someone
    re-adding the leaves would be typing.

    The names are imported rather than retyped: a guard that restates the
    vocabulary it guards is free to drift from it, which is
    ``max_priority_for`` against ``PRIORITY_MAP``'s rule.
    """

    def test_the_two_leaves_are_absent_from_the_model(self):
        fields = set(SchedulesConfig.model_fields)
        assert not (REVIEW_SCHEDULE_LEAVES & fields), (
            "schedules.review_hour/review_minute are back; the weekly project "
            "review they scheduled is estate-manager's since ADR-0005"
        )

    def test_the_siblings_that_took_over_the_job_are_all_present(self):
        """The witness that makes the absence above discriminating.

        An empty intersection proves nothing on its own — a model with no
        fields at all would satisfy it.  Three surviving ``*_review_*``
        pairs are what say the block is intact and only the vacated pair
        went.
        """
        fields = set(SchedulesConfig.model_fields)
        for prefix in ("disk_review", "log_review", "health_review"):
            assert f"{prefix}_hour" in fields
            assert f"{prefix}_minute" in fields
        assert "review_day_of_week" in fields, (
            "the shared weekly day is read by all three review jobs"
        )

    def test_nothing_reads_them(self):
        """The retired check's own question, kept because it is cheap.

        Trivially true while the fields are absent — which is exactly why
        it is not the guard, only a companion to it.
        """
        assert not attribute_reads(
            REVIEW_SCHEDULE_LEAVES,
            (REPO_ROOT / "sysadmin", REPO_ROOT / "sysadmin_tray"),
        )

    def test_the_shipped_config_does_not_set_them(self):
        """A leaf nothing reads is silently ignored, so the file must not set one.

        ``SchedulesConfig`` inherits pydantic's default ``extra="ignore"``
        — measured, and unlike ``services.yaml``'s models, which set
        ``extra="forbid"``.  So ``review_hour: 6`` in ``config.yaml`` is
        accepted, dropped, and has no effect.

        ``SNAG-CFG-004`` settled the *reporting* half of that on
        2026-08-30: :func:`sysadmin.core.config.unknown_config_keys` now
        names such a key at boot and in the reload response, so a dead
        knob is no longer silent.  It is still dead, which is why this
        guard stays — the entry was closed by making the drop visible,
        not by making the key work.
        """
        raw = yaml.safe_load(REPO_CONFIG.read_text(encoding="utf-8")) or {}
        schedules = raw.get("schedules") or {}
        assert not (REVIEW_SCHEDULE_LEAVES & set(schedules)), (
            "config.yaml sets a schedules leaf no code reads; extra='ignore' "
            "means it is dropped in silence"
        )

    def test_an_unknown_schedules_key_is_still_dropped(self):
        """``SNAG-CFG-004``'s measurement, pinned where it was taken.

        The entry closed on 2026-08-30 **without** flipping these models
        to ``extra="forbid"``: the shipped ``config.yaml`` carries ten
        keys the backend does not declare (the tray's), so a blanket
        forbid is a daemon that does not start.  The parse therefore
        behaves exactly as it did, and this test is unchanged apart from
        its name — it used to say ``…_in_silence``, and the silence is
        the half that went.

        The report is asserted next door, in
        ``tests/test_config_keys.py``.  Reading only this test would
        suggest the entry is unfixed; reading only that one, that the key
        now works.  Neither is true, so the pair is stated in both files.
        """
        parsed = SchedulesConfig(review_hour=9, briefing_hour=7)
        assert parsed.briefing_hour == 7
        assert not hasattr(parsed, "review_hour")
