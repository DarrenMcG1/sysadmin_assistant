"""Session 14 — shared defaults and config-lifted magic numbers.

Guards against the backend and tray drifting apart on host/port, and
pins the defaults for values that used to be hard-coded in routers/main.

Since 2026-08-28 it also holds the *shipped-file* half of that drift
question: the reminder ceiling ``SNAG-ESTATE-009`` now rests on, and the
two ``reminder_hours`` leaves whose agreement was held by a comment.
"""

import tokenize
import typing
from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel

from sysadmin.core.config import (
    AppConfig,
    FileOrganiserConfig,
    ProjectOrganiserConfig,
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
    # ``test_grade_bands_defaults`` stood here until Session 236 and went
    # with ``HealthGradeBands`` itself.  It is not the usual case of
    # deleting a guard beside its last finding — the rule that keeps
    # ``FROZEN_TABLES`` and ``test_none_of_them_are_defined_in_contracts``
    # alive — because the thing it guarded cannot come back *here*: the
    # repository health score left with the projects domain on 2026-08-13
    # (ADR-0005) and those bands are argued for in estate-manager.  What
    # replaces it is ``TestTheOrganiserBlockIsTrimmedToItsReaders`` below,
    # which guards the trim rather than the departed arithmetic.

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
        assert cfg.agents.project_organiser.projects_root == "/home/gaddi/projects"
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


class TestTheOrganiserBlockIsTrimmedToItsReaders:
    """Session 236 — what survives ``agents.project_organiser``, and why.

    The agent left on 2026-08-13 (ADR-0005) and its configuration stayed
    behind: thirteen leaves across five nested models, parsed by pydantic
    and — for all but two of them — read by nothing.  That is
    ``SNAG-CFG-001``'s shape, and the trim that removed it has to be
    guarded from both sides, because **a key in the file and a field in
    the model are two statements of one setting that fail in opposite
    directions**.  A key with no field is loud (``config_keys`` names the
    orphan on every reload); a field with no key is silent (the value
    falls back to the model default, which for ``enabled`` would have
    turned the file's recorded ``false`` into a parsed ``true``).

    So there are two guards with different reaches, and the difference is
    measured rather than asserted:

    - the **file** half is exact.  A key is a key; there is nothing to
      collide with, so it catches every leaf re-added to ``config.yaml``.
    - the **model** half keys on ``attribute_reads``, which compares the
      final segment of an attribute load — ``ast.Attribute.attr`` — and
      therefore cannot tell this block's leaf from another block's leaf
      of the same name.  Driven at the twelve deleted leaves it reports
      **seven** correctly unread (``max_todo_penalty``, ``todo_patterns``,
      ``stale_branch_days``, ``track_todos``, ``idle_nudges``,
      ``branch_actions``, ``estate``) and is masked on **five** by
      collisions elsewhere in the tree: ``enabled`` (44 reads),
      ``scan_interval_hours`` (7), ``weekly_review`` (3),
      ``alert_threshold`` (1, the unit sweep's patience knob) and
      ``grade_bands`` (1, ``ReliabilityGradeBands``).

    The residue is stated rather than implied: a **model-only** field
    whose name collides — ``weekly_review`` is the one real specimen,
    since it was never in the file — escapes both guards.  It is small
    and it is the honest limit; narrowing ``attribute_reads`` to a
    qualified path would make it a second implementation of the attribute
    chain, which is ``SNAG-DB-003``'s shape.
    """

    #: The leaves deleted on 2026-09-14, as the falsification population.
    #: Restoring any of them must turn one of these tests red.
    TRIMMED = (
        "enabled",
        "scan_interval_hours",
        "stale_branch_days",
        "track_todos",
        "todo_patterns",
        "grade_bands",
        "alert_threshold",
        "weekly_review",
        "max_todo_penalty",
        "branch_actions",
        "estate",
        "idle_nudges",
    )

    def _organiser_block(self) -> dict:
        raw = yaml.safe_load(REPO_CONFIG.read_text(encoding="utf-8"))
        return raw["agents"]["project_organiser"]

    def test_the_shipped_file_sets_only_the_reloadable_leaf(self):
        """The exact half.  Every re-added key is caught here, collision or not."""
        assert set(self._organiser_block()) == {"projects_root"}

    def test_no_trimmed_leaf_returned_to_the_file(self):
        """Stated positively as well, so a red names the leaf rather than a set diff."""
        block = self._organiser_block()
        assert [leaf for leaf in self.TRIMMED if leaf in block] == []

    def test_every_declared_field_has_a_reader(self):
        """The model half.  A field nothing reads is the shape that was removed.

        Driven at ``sysadmin/`` alone: a leaf read only by its own tests
        is a leaf kept alive by the thing testing it.
        """
        unread = [
            name
            for name in ProjectOrganiserConfig.model_fields
            if not attribute_reads(frozenset({name}), [REPO_ROOT / "sysadmin"])
        ]
        assert unread == []

    def test_the_model_guard_is_falsified_by_seven_of_the_twelve(self):
        """The guard above is driven at the defect, and its reach is pinned.

        Seven of the twelve deleted leaves have no same-named reader
        anywhere under ``sysadmin/``, so re-adding any of them to
        :class:`ProjectOrganiserConfig` turns
        ``test_every_declared_field_has_a_reader`` red.  Pinning the
        number is what stops the reach being quietly overstated: if a
        future module happens to read a field called ``estate``, this
        goes red and the docstring above is the thing to correct.
        """
        caught = [
            leaf
            for leaf in self.TRIMMED
            if not attribute_reads(frozenset({leaf}), [REPO_ROOT / "sysadmin"])
        ]
        assert sorted(caught) == [
            "branch_actions",
            "estate",
            "idle_nudges",
            "max_todo_penalty",
            "stale_branch_days",
            "todo_patterns",
            "track_todos",
        ]

    def test_discovery_depth_is_live_and_deliberately_unset(self):
        """The asymmetry the whole sitting turned on, pinned in both directions.

        ``discovery_depth`` has two readers in ``units/agent.py`` and
        appears in no shipped ``config.yaml``.  A trim scoped to the file
        cannot see it, and would have read its absence there as evidence
        it was dead — the handoff that opened this sitting named seven
        readers and only ``projects_root``.  It is not written into the
        file either: a value stated in two places is free to disagree
        with itself.

        **The declaration is asserted, and the first draft of this test
        did not assert it.**  Driven as a mutation, deleting the field
        from :class:`ProjectOrganiserConfig` left all five of these tests
        green — ``attribute_reads`` measures ``units/agent.py``, which the
        deletion does not touch, and
        ``test_every_declared_field_has_a_reader`` merely loops over one
        field fewer.  A no-op mutation is not a control, so the missing
        half is here.  The full suite does catch that deletion, in
        ``tests/test_units_api.py::test_project_refs_come_from_the_registry``
        and as an ``AttributeError`` rather than as a statement about
        this block — which is cover, not the thing this docstring claims.
        """
        assert "discovery_depth" in ProjectOrganiserConfig.model_fields
        reads = attribute_reads(frozenset({"discovery_depth"}), [REPO_ROOT / "sysadmin"])
        assert len(reads) == 2
        assert all("units/agent.py" in hit for hit in reads)
        assert "discovery_depth" not in self._organiser_block()


# --- The general case of the organiser trim (Session 237) ---------------


def _submodels(annotation) -> list[type[BaseModel]]:
    """Every :class:`BaseModel` reachable from a field annotation.

    Recursing through :func:`typing.get_args` rather than testing the
    annotation alone is what reaches a model nested inside ``list[...]``,
    ``dict[str, ...]`` or an optional.  The population is empty today —
    every container in :class:`AppConfig` is a bare model — and it is
    written this way so that the first wrapped sub-config does not
    silently take its whole subtree out of the sweep below.
    """
    found: list[type[BaseModel]] = []
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        found.append(annotation)
    for arg in typing.get_args(annotation):
        found.extend(_submodels(arg))
    return found


def _config_field_names(
    root_model: type[BaseModel] = AppConfig,
) -> tuple[frozenset[str], frozenset[str]]:
    """A model's whole field tree, split into leaves and containers.

    Parameterised rather than copied for :class:`TestEveryTrayLeafHasAReader`
    below, which asks the same question of :class:`~sysadmin_tray.config.TrayConfig`
    against a different root directory.  A second walker would be a second
    implementation of one derivation — ``SNAG-DB-003``'s shape — and the two
    guards differ only in *what* they walk and *where* they look for readers,
    so that is what varies.
    """
    leaves: set[str] = set()
    containers: set[str] = set()

    def walk(model: type[BaseModel]) -> None:
        for name, field in model.model_fields.items():
            subs = _submodels(field.annotation)
            if subs:
                containers.add(name)
                for sub in subs:
                    walk(sub)
            else:
                leaves.add(name)

    walk(root_model)
    return frozenset(leaves), frozenset(containers)


class TestEveryConfigLeafHasAReader:
    """Session 237 — the general case of Session 236's block-scoped guard.

    That sitting trimmed ``agents.project_organiser`` and pinned *its*
    twelve leaves.  The question it left is the one this class answers:
    **is a declared-and-unread leaf a property something computes, or a
    thing somebody has to notice?**  Walking the whole tree at the time
    found four survivors, every one of them present in the **first
    commit** and never given or deprived of a reader by any commit since
    — birth defects rather than residue of a domain that left, which is
    what makes a standing guard the right shape and a one-off sweep the
    wrong one.

    The four, and why each was removed rather than kept:

    - ``personal_assistant.api_prefix`` — unreadable by construction.
      Its sibling endpoints are absolute and already carry ``/api``, so
      any reader builds ``/api/api/v2/...``.
    - ``agents.sysadmin.thresholds.cpu_sustained_percent`` and
      ``.cpu_sustained_minutes`` — a check nothing performs, whose
      population is empty: one five-minute sample at or above 90% across
      3,497 snapshots, against a declared ten minutes, while the z-score
      path raised ``Unusual CPU usage`` 67 times.
    - ``agents.file_organiser.output_dir`` — a destination that stopped
      existing in the port from ``home_audit.py``; findings go to
      ``file_audits``.

    **Two halves with different reaches, and the difference is measured.**
    The leaf half is the finding population and was four.  The container
    half — a whole sub-config nothing reads — ships with an **empty**
    finding population and says so rather than leaving the silence to be
    read as coverage, which is ``ports_checked``'s rule: nought-because-clean
    must not be served as nought-because-nobody-looked.

    The reach limit is ``SNAG-CFG-008`` and is stated rather than
    claimed.  ``attribute_reads`` compares ``ast.Attribute.attr``, the
    final segment, so a leaf whose name collides with a live one
    elsewhere in the tree is masked — ``enabled`` has 44 readers and
    would answer for any block's ``enabled``.  Narrowing it to a
    qualified path would make it a second implementation of the attribute
    chain, which is ``SNAG-DB-003``'s shape, so the masking stays and is
    named.

    It is driven at ``sysadmin/`` alone.  A leaf read only by the test
    that exercises it is a leaf kept alive by the thing testing it, and
    ``tests`` is a consumer package on purpose everywhere else in this
    repository — here that would make the guard unfalsifiable by its own
    fixtures.
    """

    #: The leaves deleted on 2026-09-14, as the falsification population.
    #: Restoring any of them to :class:`AppConfig` must turn
    #: ``test_no_declared_leaf_is_unread`` red.
    TRIMMED = (
        "api_prefix",
        "cpu_sustained_percent",
        "cpu_sustained_minutes",
        "output_dir",
    )

    def test_the_walk_reaches_the_whole_tree(self):
        """The premise, without which every assertion below passes vacuously.

        A walker that stopped descending would sweep a handful of
        top-level fields, find them all read, and report clean — the
        failure ``test_no_config_model_forbids_unknown_keys`` guards
        against one module over, where a floor exists so that ``strict
        == 0`` cannot pass over an emptied population.

        Two statements, because a count alone is weak.  The floor
        catches a walk that collapses; the named leaf catches one that
        stops at depth one, since ``gpu_vram_warning_percent`` is three
        levels down (``agents.sysadmin.thresholds``) and is reachable
        only by recursing twice.  Both are floors rather than equalities:
        the tree legitimately shrank by five models on 2026-09-14 and
        will again, and a guard that has to be nudged past a red on every
        trim is one nobody reads.
        """
        leaves, containers = _config_field_names()
        assert len(leaves) >= 100, "the field tree shrank; re-measure before trusting this"
        assert len(containers) >= 25, "the field tree shrank; re-measure before trusting this"
        assert "gpu_vram_warning_percent" in leaves
        assert "thresholds" in containers

    def test_no_declared_leaf_is_unread(self):
        """The finding half.  A leaf nothing reads is the shape removed."""
        leaves, _ = _config_field_names()
        unread = sorted(
            name
            for name in leaves
            if not attribute_reads(frozenset({name}), [REPO_ROOT / "sysadmin"])
        )
        assert unread == []

    def test_no_declared_sub_config_is_unread(self):
        """The half with nothing in it, asserted anyway.

        A container nothing reads takes its entire subtree out of the
        sweep above — every leaf beneath it would be reachable only
        through a name no code loads.  Empty today across all 31
        containers, which is a measurement and not an assumption.
        """
        _, containers = _config_field_names()
        unread = sorted(
            name
            for name in containers
            if not attribute_reads(frozenset({name}), [REPO_ROOT / "sysadmin"])
        )
        assert unread == []

    def test_the_guard_is_falsified_by_all_four_trimmed_leaves(self):
        """The guard is driven at the defect, and its reach is pinned.

        All four deleted names are free of collisions, so re-declaring
        any of them turns ``test_no_declared_leaf_is_unread`` red.  That
        is a stronger position than Session 236's block, where five of
        twelve were masked — and it is luck of the naming rather than a
        property of the fix, so it is pinned: should a future module read
        something called ``output_dir``, this goes red and the reach
        claimed in the docstring is the thing to correct, not this
        assertion.
        """
        caught = [
            leaf
            for leaf in self.TRIMMED
            if not attribute_reads(frozenset({leaf}), [REPO_ROOT / "sysadmin"])
        ]
        assert sorted(caught) == sorted(self.TRIMMED)

    def test_prose_about_a_removed_leaf_is_not_a_reader(self):
        """The commit that removed them names all four in docstrings.

        Each removal left a paragraph saying why the setting is absent,
        so ``grep`` now finds ``cpu_sustained`` in ``config.py`` and a
        lexical guard would report the deleted fields as alive.  A
        docstring is an ``ast.Constant``; a read is an ``ast.Attribute``
        in ``Load`` context.  This asserts the difference at the real
        file rather than at a synthetic one, because the prose is the
        specimen.
        """
        source = (REPO_ROOT / "sysadmin" / "core" / "config.py").read_text(
            encoding="utf-8"
        )
        assert "cpu_sustained_percent" in source
        assert attribute_reads(
            frozenset({"cpu_sustained_percent"}), [REPO_ROOT / "sysadmin"]
        ) == []

    def test_no_trimmed_leaf_returned_to_the_shipped_file(self):
        """The exact half, which no collision can mask.

        ``config_keys`` would name a returning key as unknown on every
        reload, so this is not the only speaker — it is the one that
        fails in CI rather than in a log line nobody opens.
        """
        raw = yaml.safe_load(REPO_CONFIG.read_text(encoding="utf-8"))
        text = yaml.safe_dump(raw)
        assert [leaf for leaf in self.TRIMMED if f"{leaf}:" in text] == []


class TestEveryTrayLeafHasAReader:
    """Session 238 — the same question asked one seam over.

    :class:`TestEveryConfigLeafHasAReader` walks ``AppConfig`` against
    ``sysadmin/``.  Driving the identical walk at
    :class:`~sysadmin_tray.config.TrayConfig` against ``sysadmin_tray/``
    found **19** leaves, **0** containers and exactly one survivor:
    ``dashboard_url``, decided by the owner on 2026-09-14 and removed
    with its ``config.yaml`` key and its
    :data:`~sysadmin_tray.config.TRAY_SECTION_KEYS` entry.

    **The recurrence this guards against is the one that has actually
    happened here, which is the reverse of the argument one seam over.**
    The four leaves trimmed from ``AppConfig`` entered in the first
    commit and no commit has ever added or removed a reader for any of
    them, so what a guard there catches is a leaf *arriving* unread.
    ``dashboard_url`` had a reader and lost it: ``81b3bfb`` wired it to
    ``TrayApp._open_dashboard``, which opened it in a browser, and
    ``3f68448`` (2026-02-13, *"add native dashboard"*) replaced that
    body with ``self._dashboard.toggle_visibility()``.  The menu item
    survived the refactor and the leaf outlived its mechanism —
    ``webbrowser`` is imported nowhere under ``sysadmin_tray/`` — for
    **seven months**.  A reader deleted by a refactor is the commoner
    event and the only one of the two this box has demonstrated.

    **The root is ``sysadmin_tray/`` alone, and ``dashboard_url`` is the
    case that rule was written for.**  The sibling guard excludes
    ``tests`` because a leaf read only by the thing testing it is a leaf
    kept alive by its own fixtures; this leaf was asserted three times in
    ``tests/test_tray/test_config.py`` and read by no widget, so a guard
    that admitted ``tests`` as a root would have found a reader and
    shipped green over the defect it exists to find.

    Two limits, both stated rather than claimed away:

    - ``SNAG-CFG-008``'s reach applies unchanged.  ``attribute_reads``
      compares the last segment of an attribute chain, so a leaf whose
      name collides with a live one elsewhere under ``sysadmin_tray/``
      is masked.  Pinned for the specimen by
      ``test_the_guard_is_falsified_by_the_trimmed_leaf`` and not
      claimed for the other eighteen.
    - A **third** half exists here that ``AppConfig`` has not got, and
      only two of the three are guarded.  A key needs its
      ``config.yaml`` line, its allowlist entry *and* its field;
      ``test_every_shipped_key_is_read`` catches a line with no
      allowlist entry and this class catches a field with no reader, but
      a line and an entry with no field are silently dropped, because
      ``TrayConfig`` sets no ``model_config`` and pydantic's default is
      ``extra="ignore"`` — ``SNAG-CFG-004``'s asymmetry on the tray's
      side of the seam.

    There is deliberately no shipped-file assertion to match
    ``test_no_trimmed_leaf_returned_to_the_shipped_file``.  That one
    earns its place by being *the speaker that fails in CI* where
    ``config_keys`` only writes a log line; here the other speaker,
    ``tests/test_tray/test_config.py::TestTraySectionReport::test_every_shipped_key_is_read``,
    already fails in CI against the real file, so a second would be one
    fact with two speakers.
    """

    def test_the_walk_reaches_the_whole_tray_model(self):
        """The premise, without which the assertions below pass vacuously.

        A floor rather than an equality, for the sibling guard's reason:
        the model legitimately lost a field on 2026-09-14 and may lose
        another, and a guard needing a nudge past a red on every trim is
        one nobody reads.  The named leaf is the second statement —
        ``backend_unreachable_grace_seconds`` is a real field and a
        walker returning an empty set cannot contain it.
        """
        leaves, _ = _config_field_names(TrayConfig)
        assert len(leaves) >= 15, "TrayConfig shrank; re-measure before trusting this"
        assert "backend_unreachable_grace_seconds" in leaves

    def test_no_declared_leaf_is_unread(self):
        """The finding half.  A leaf nothing reads is the shape removed."""
        leaves, _ = _config_field_names(TrayConfig)
        unread = sorted(
            name
            for name in leaves
            if not attribute_reads(frozenset({name}), [REPO_ROOT / "sysadmin_tray"])
        )
        assert unread == []

    def test_no_declared_sub_config_is_unread(self):
        """Vacuous in two ways today, and armed for the day it is not.

        ``TrayConfig`` is flat — **0** containers — so there is no
        container to be unread, where the sibling guard's equivalent has
        31 and finds none.  It is written now rather than when the first
        sub-model is nested, because a container nothing reads takes its
        whole subtree out of the test above and the failure would be
        silence.
        """
        _, containers = _config_field_names(TrayConfig)
        # may-not-turn: TrayConfig is flat, so `containers` is empty by
        # construction and that emptiness is what the assert states — there is
        # no container here that could be unread.  The identical comprehension
        # in TestEveryConfigLeafHasAReader above runs over AppConfig's 31, so
        # the shape is witnessed turning; what is nought here is the
        # population, never the reader.  It arms itself the day a sub-model is
        # nested, which is the whole reason it is written before one is.
        unread = sorted(
            name
            for name in containers
            if not attribute_reads(frozenset({name}), [REPO_ROOT / "sysadmin_tray"])
        )
        assert unread == []

    def test_the_guard_is_falsified_by_the_trimmed_leaf(self):
        """Driven at the defect, which is what makes the guard a guard.

        ``dashboard_url`` collides with nothing under ``sysadmin_tray/``,
        so re-declaring it on :class:`~sysadmin_tray.config.TrayConfig`
        turns ``test_no_declared_leaf_is_unread`` red.  Should a future
        widget read something else called ``dashboard_url``, this goes
        red and the reach claimed in the class docstring is the thing to
        correct rather than this assertion.
        """
        assert (
            attribute_reads(
                frozenset({"dashboard_url"}), [REPO_ROOT / "sysadmin_tray"]
            )
            == []
        )

    def test_the_note_explaining_the_removal_is_comment_only(self):
        """The sibling's prose test, one notch further and asserted exactly.

        That one works because a docstring survives parsing as an
        ``ast.Constant``: grep finds it, the tree holds it as a
        constant, and the test pins that a constant is not a read.  The
        note left where ``dashboard_url`` was declared is a plain
        **comment**, which the tokenizer discards outright, so it is
        invisible to every AST instrument and visible only to a lexical
        one — ``grep -c dashboard_url sysadmin_tray/config.py`` returns
        1 against ``attribute_reads``' nothing.

        Stated as an equality over ``tokenize`` rather than by
        restating ``attribute_reads(...) == []`` one test above.  That
        would be one fact with two speakers and, worse, unfalsifiable
        one-to-one: the mutation that reddens it reddens its sibling.
        This asks the question only this test asks — *is every
        occurrence of the name a comment?* — so a field, a string or a
        read re-entering the file turns it red while the reachability
        claim stays where it is measured.
        """
        path = REPO_ROOT / "sysadmin_tray" / "config.py"
        source = path.read_text(encoding="utf-8")
        with path.open("rb") as handle:
            comments = "\n".join(
                token.string
                for token in tokenize.tokenize(handle.readline)
                if token.type == tokenize.COMMENT
            )
        in_file = source.count("dashboard_url")
        assert in_file > 0, "the note explaining the removal is gone"
        assert comments.count("dashboard_url") == in_file
