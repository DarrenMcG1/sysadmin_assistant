"""Session 136 — ``SNAG-CFG-004``: a config key nothing declares is named.

The entry asked whether ``sysadmin/core/config.py``'s 37 models should
set ``extra="forbid"`` as ``sysadmin/monitor/services.py``'s four do. The
measurement that decided it is :class:`TestTheShippedFileIsTheRefutation`:
the file already carries ten keys the backend does not declare, all owned
by the tray, so a blanket forbid is a daemon that does not boot rather
than a trade-off to weigh.

What shipped instead reports and cannot refuse. So the drop is still
silent at the *parse* — ``test_the_drop_is_unchanged_and_only_the_silence_
is_gone`` pins that pair deliberately — and the report is what makes the
line visible, on the two surfaces an operator is actually holding: the
boot journal, and the response to their own ``POST /api/sysadmin/reload``.

Every test here was driven at a mutation that must break it before it was
written down.
"""

from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, Field

from sysadmin.core.config import (
    FOREIGN_KEYS,
    AppConfig,
    default_config_path,
    parse_config,
    unknown_config_keys,
)
from sysadmin.core.config_keys import KeyReport, model_in, report_for_file, walk
from sysadmin_tray.config import NOTIFICATIONS_TRAY_KEYS, load_tray_config


@pytest.fixture
def shipped_raw() -> dict:
    """The real config.yaml, read raw. Never through ``load_config``.

    ``load_config`` is ``set_config(parse_config(...))``, so a helper that
    looks like a read installs what it read — which would leave the test
    process holding whatever specimen a mutation produced.
    """
    return yaml.safe_load(default_config_path().read_text(encoding="utf-8")) or {}


def mutated(raw: dict, path: str, value=1) -> dict:
    """A deep copy of ``raw`` with one dotted path added."""
    import copy

    out = copy.deepcopy(raw)
    node = out
    parts = path.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
    return out


class TestTheShippedFileIsTheRefutation:
    """The measurement that decided the entry against its own headline."""

    def test_the_shipped_file_declares_every_key_it_sets(self):
        """Clean — but only once the foreign region is declared.

        This is the *positive* half. On its own it is satisfied by an
        exemption set that is too broad, which is why it is never read
        without :class:`TestTheBoundaryIsDerivedNotAsserted` beside it.
        """
        report = unknown_config_keys()
        assert report.walked, "the walk did not happen; its empty list is blind"
        assert report.unknown == []
        assert report.unwalkable == []
        assert report.clean

    def test_without_the_declaration_the_shipped_file_would_not_be_clean(
        self, shipped_raw
    ):
        """The refutation, driven rather than quoted.

        With no foreign region declared, the walk finds exactly the ten
        keys that make ``extra="forbid"`` unbootable on this box. This is
        the entry's headline fix, measured.
        """
        report = walk(shipped_raw, AppConfig, foreign=())
        assert len(report.unknown) == 10
        assert "tray" in report.unknown
        assert all(
            key == "tray" or key.startswith("notifications.tray.")
            for key in report.unknown
        ), report.unknown

    def test_every_one_of_them_is_a_key_the_tray_actually_reads(self, shipped_raw):
        """Not merely undeclared here — declared *there*.

        An undeclared key is only legitimately foreign if some other
        parser reads it. Otherwise the honest verdict is that the shipped
        file carries ten dead keys, which is the entry over again at ten
        times the size.
        """
        report = walk(shipped_raw, AppConfig, foreign=())
        for key in report.unknown:
            if key == "tray":
                continue
            leaf = key.removeprefix("notifications.tray.")
            assert leaf in NOTIFICATIONS_TRAY_KEYS, key


class TestTheBoundaryIsDerivedNotAsserted:
    """``FOREIGN_KEYS`` is hand-written; nothing may let it drift."""

    def test_it_matches_what_the_tray_declares_it_reads(self):
        """The pin. ``sysadmin.core`` may not import the tray, so the
        agreement is asserted here instead — ``syslog_priority`` against
        ``journal.PRIORITY_MAP``'s treatment.
        """
        derived = {"tray"} | {
            f"notifications.tray.{key}" for key in NOTIFICATIONS_TRAY_KEYS
        }
        assert FOREIGN_KEYS == derived

    def test_no_exemption_names_a_key_this_process_declares(self):
        """A stale exemption is a hole, and it opens silently.

        The day a ``tray`` field is added to ``AppConfig``, or a calm
        tunable is promoted into ``TrayNotificationsConfig``, the
        exemption stops describing a foreign key and starts hiding a
        typo in one of ours.
        """
        for path in sorted(FOREIGN_KEYS):
            declared = walk(mutated({}, path), AppConfig, foreign=())
            assert declared.unknown == [path], (
                f"{path} is exempted but {AppConfig.__name__} declares it; "
                "the exemption now hides a key this process reads"
            )

    def test_mute_services_is_not_exempt(self, shipped_raw):
        """Rule 4's exception, and the reason the exemption is per leaf.

        ``notifications.tray.mute_services`` is read *here* — reliability
        waives deductions for an expected-down service — so a subtree
        exemption would make ``mute_servicess`` silent on the one key
        under that section the backend depends on.
        """
        assert "notifications.tray.mute_services" not in FOREIGN_KEYS
        report = walk(
            mutated(shipped_raw, "notifications.tray.mute_servicess", []),
            AppConfig,
            foreign=FOREIGN_KEYS,
        )
        assert "notifications.tray.mute_servicess" in report.unknown

    def test_a_typo_in_a_tray_owned_leaf_is_still_caught(self, shipped_raw):
        """A benefit of exempting leaves rather than the subtree.

        The correct spelling is exempt and the typo is not, so a
        misspelt calm tunable is reported even though the backend never
        reads it. It cannot fix the key; it can say the line is dead.
        """
        report = walk(
            mutated(shipped_raw, "notifications.tray.reminder_hourss", 6),
            AppConfig,
            foreign=FOREIGN_KEYS,
        )
        assert "notifications.tray.reminder_hourss" in report.unknown

    def test_a_typo_inside_the_tray_section_is_the_stated_blind_spot(
        self, shipped_raw
    ):
        """Asserted so the limit is a decision rather than a surprise.

        ``tray:`` is exempt whole, so nothing under it is judged. Holding
        a model of another parser's section here is the second-owner
        defect; the tray is where that section can be reported on.
        """
        report = walk(
            mutated(shipped_raw, "tray.status_poll_secondss", 5),
            AppConfig,
            foreign=FOREIGN_KEYS,
        )
        assert report.unknown == []


class TestTheEntrysOwnSpecimen:
    """``briefing_hourr: 9`` — the line the entry measured."""

    def test_it_is_named(self, shipped_raw):
        report = walk(
            mutated(shipped_raw, "schedules.briefing_hourr", 9),
            AppConfig,
            foreign=FOREIGN_KEYS,
        )
        assert report.unknown == ["schedules.briefing_hourr"]

    def test_the_drop_is_unchanged_and_only_the_silence_is_gone(self, tmp_path):
        """The pair that states what this fix did and did not do.

        The parse still accepts the typo and still ignores it — no model
        gained ``extra="forbid"``, which is the whole reason the daemon
        still boots. What changed is that the drop is now *named*. A
        later session reading only the first assertion would conclude the
        entry is unfixed; reading only the second, that the key now
        works.
        """
        raw = yaml.safe_load(default_config_path().read_text(encoding="utf-8"))
        raw["schedules"]["briefing_hourr"] = raw["schedules"].pop("briefing_hour", 6)
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump(raw), encoding="utf-8")

        parsed = parse_config(path)
        assert parsed.schedules.briefing_hour == 6, "still dropped, still defaulted"

        report = report_for_file(path, AppConfig, foreign=FOREIGN_KEYS)
        assert "schedules.briefing_hourr" in report.unknown, "no longer silent"


class TestTheWalkerFollowsPydanticRatherThanRestatingIt:
    """Rule 2. The tree it walks is the one pydantic built."""

    def test_an_alias_is_accepted_as_the_file_spells_it(self, shipped_raw):
        """``DatabaseConfig`` declares ``schema_`` with ``alias="schema"``.

        A walker reading only field names would report the one key in
        this tree that is spelled deliberately — and it is set in the
        shipped file.
        """
        report = walk(
            mutated(shipped_raw, "database.schema", "sysadmin"),
            AppConfig,
            foreign=FOREIGN_KEYS,
        )
        assert report.unknown == []

    def test_it_descends_into_a_list_of_models(self, shipped_raw):
        """``agents.log_aggregator.sources`` is ``list[LogSource]``.

        Reported with the index, because two sources with the same typo
        are two lines to fix.
        """
        raw = mutated(shipped_raw, "schedules.unused", 1)
        raw["agents"]["log_aggregator"]["sources"][0]["severity_filterr"] = "warning"
        report = walk(raw, AppConfig, foreign=FOREIGN_KEYS)
        assert (
            "agents.log_aggregator.sources[0].severity_filterr" in report.unknown
        )

    def test_model_in_unwraps_containers_and_optionals(self):
        class Leaf(BaseModel):
            x: int = 0

        class Holder(BaseModel):
            plain: Leaf = Field(default_factory=Leaf)
            listed: list[Leaf] = Field(default_factory=list)
            optional: Leaf | None = None
            scalar: str = ""

        fields = Holder.model_fields
        assert model_in(fields["plain"].annotation) is Leaf
        assert model_in(fields["listed"].annotation) is Leaf
        assert model_in(fields["optional"].annotation) is Leaf
        assert model_in(fields["scalar"].annotation) is None


class TestNotKnowingIsNeverServedAsClean:
    """Rule 3 and rule 5 — ``ports_checked``'s rule, twice."""

    def test_a_subtree_it_cannot_read_is_reported(self, shipped_raw):
        """A scalar where a model belongs means the subtree went unread.

        Skipping it would count it clean, which is the silence this
        module exists to end, one level down.
        """
        raw = dict(shipped_raw)
        raw["schedules"] = 6
        report = walk(raw, AppConfig, foreign=FOREIGN_KEYS)
        assert report.unwalkable == ["schedules"]
        assert not report.clean, "unknown==[] must not read as clean here"

    def test_a_walk_that_could_not_happen_is_not_clean(self, tmp_path):
        report = report_for_file(
            tmp_path / "absent.yaml", AppConfig, foreign=FOREIGN_KEYS
        )
        assert report.walked is False
        assert report.unknown == []
        assert not report.clean

    def test_an_unparseable_file_is_not_clean(self, tmp_path):
        path = tmp_path / "config.yaml"
        path.write_text("service: {host: [unclosed\n", encoding="utf-8")
        report = report_for_file(path, AppConfig, foreign=FOREIGN_KEYS)
        assert report.walked is False
        assert not report.clean

    def test_an_empty_section_is_clean_rather_than_unwalkable(self, shipped_raw):
        """``notifications:`` with nothing under it declares no key.

        Distinguished from the scalar case deliberately: ``None`` is an
        absence pydantic already accepted, not a shape the walker failed
        to follow.
        """
        raw = dict(shipped_raw)
        raw["events"] = None
        report = walk(raw, AppConfig, foreign=FOREIGN_KEYS)
        assert report.unwalkable == []


class TestTheReportCannotRefuse:
    """Rule 1, asserted at the type rather than trusted as an intention."""

    def test_the_walk_returns_and_never_raises_on_a_valid_file(self, shipped_raw):
        assert isinstance(walk(shipped_raw, AppConfig), KeyReport)

    def test_a_file_full_of_unknown_keys_still_parses(self, tmp_path):
        """The property the whole decision rests on.

        Ten unknown keys and the config still loads — which is what
        ``extra="forbid"`` would have turned into a refusal to start.
        """
        path = tmp_path / "config.yaml"
        path.write_text(
            yaml.safe_dump({f"nonsense_{i}": i for i in range(10)}), encoding="utf-8"
        )
        parsed = parse_config(path)
        assert parsed.service.port  # it loaded
        report = report_for_file(path, AppConfig, foreign=FOREIGN_KEYS)
        assert len(report.unknown) == 10


class TestTheTrayStillLoadsItsOwnKeys:
    """The constants were lifted out of loops; the loops must still run."""

    def test_the_shipped_file_reaches_the_tray_unchanged(self):
        config = load_tray_config()
        assert config.reminder_hours == 24.0
        assert config.api_url.endswith(":8500")


# ── The retired check's detector, re-homed ────────────────────────────
#
# ``check_config_extras_ignored`` measured the asymmetry the entry named:
# 0 of 37 models in config.py forbid unknown keys, 4 of 4 in services.py
# do. It retires with the entry, and the detector does not
# (``FROZEN_TABLES``' rule) — but its *meaning is inverted*, which is the
# part worth carrying.
#
# The check could not have witnessed this closure. It watched two counts
# that this fix does not move, so it would have gone on reporting
# ``match`` — "still holds" — over a landed fix, indefinitely. That is
# `check_review_schedule_unread`'s defect from one entry earlier, and it
# is not a flaw in how the check was written: the entry was closed by a
# route the check did not anticipate.
#
# So the same walk now guards the opposite claim. Those counts must
# **stay** where they are, because the ten tray-owned keys make
# ``extra="forbid"`` on config.py a daemon that does not boot. What was
# evidence of a defect is now evidence of a deliberate asymmetry.


def forbidding_models(path: Path) -> tuple[int, int]:
    """``(pydantic models, those setting extra="forbid")`` in one module.

    An AST walk rather than a substring count: ``"forbid"`` appears in
    prose and in docstrings, and the question is how many *classes* carry
    the setting rather than how often the word is written.
    """
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    models = strict = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(
            getattr(base, "id", getattr(base, "attr", "")) == "BaseModel"
            for base in node.bases
        ):
            continue
        models += 1
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and sub.value == "forbid":
                strict += 1
                break
    return models, strict


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_MODULE = REPO_ROOT / "sysadmin" / "core" / "config.py"
SERVICES_MODULE = REPO_ROOT / "sysadmin" / "monitor" / "services.py"


class TestTheAsymmetryIsDeliberateAndStays:
    """The retired check's walk, guarding the opposite claim."""

    def test_no_config_model_forbids_unknown_keys(self):
        """Flipping any of them makes the daemon refuse to start.

        Not a style preference: ``config.yaml`` is read by two programs
        and the tray owns ten keys in it, so the models describing the
        backend's half are not a description of the file.
        """
        models, strict = forbidding_models(CONFIG_MODULE)
        assert models >= 37, "the module shrank; re-measure before trusting this"
        assert strict == 0, (
            f"{strict} model(s) in sysadmin/core/config.py now forbid unknown "
            "keys — the shipped config.yaml carries keys the tray owns, so "
            "this is a daemon that does not boot. SNAG-CFG-004 closed by "
            "reporting instead; see sysadmin/core/config_keys.py rule 1."
        )

    def test_every_services_model_still_forbids_them(self):
        """The other direction. ``services.yaml`` has one modelled owner
        and no foreign region, so it can afford to refuse — and a model
        quietly losing the setting would close the asymmetry the wrong
        way without anything saying so.
        """
        models, strict = forbidding_models(SERVICES_MODULE)
        assert models == strict == 4

    def test_the_walk_counts_classes_rather_than_the_word(self, tmp_path):
        """The detector, shown failing — it must not count prose.

        Two models, one docstring saying "forbid", one real setting.
        """
        specimen = tmp_path / "specimen.py"
        specimen.write_text(
            "from pydantic import BaseModel, ConfigDict\n"
            "class Decoy(BaseModel):\n"
            '    """We could forbid extras here. forbid forbid."""\n'
            "    x: int = 0\n"
            "class Strict(BaseModel):\n"
            '    model_config = ConfigDict(extra="forbid")\n',
            encoding="utf-8",
        )
        assert forbidding_models(specimen) == (2, 1)

    def test_the_entrys_headline_fix_does_not_parse_the_shipped_file(self):
        """``extra="forbid"`` on ``AppConfig``, executed rather than argued.

        A subclass is enough to make the point: pydantic applies the
        setting per model, so this forbids only the *top level*, and the
        shipped file fails there already on ``tray:``. The nine leaves
        under ``notifications.tray:`` would fail the same way one model
        down. This is what the daemon would do in its lifespan — where
        the failure is a unit that will not start.
        """
        from pydantic import ConfigDict

        class StrictAppConfig(AppConfig):
            model_config = ConfigDict(extra="forbid")

        raw = yaml.safe_load(default_config_path().read_text(encoding="utf-8"))
        with pytest.raises(Exception) as caught:
            StrictAppConfig.model_validate(raw)
        assert "tray" in str(caught.value)

        # …and the same file parses today, which is the behaviour kept.
        assert AppConfig.model_validate(raw).service.port == 8500


class TestTheBootPathIsWired:
    """The report is only worth having where it is actually reached.

    An AST assertion rather than a drive, matching
    ``tests/test_reload.py``'s existing treatment of the lifespan: the
    real one opens an engine and a scheduler, and what needs guarding
    here is one call that is easy to drop and impossible to miss the
    absence of — a boot that says nothing looks exactly like a boot with
    nothing to say.
    """

    def test_the_lifespan_asks_for_the_report(self):
        import ast

        source = (REPO_ROOT / "sysadmin" / "main.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        lifespan = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan"
        )
        called = {
            node.func.id
            for node in ast.walk(lifespan)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "unknown_config_keys" in called, (
            "the lifespan no longer asks which config keys are unread; a boot "
            "that says nothing is indistinguishable from one with nothing to say"
        )

    def test_it_cannot_take_the_boot_down(self):
        """The call is guarded, and the guard is what makes rule 1 true
        in practice rather than only by the walker's return type.
        """
        import ast

        source = (REPO_ROOT / "sysadmin" / "main.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        lifespan = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan"
        )
        guarded = [
            handler
            for node in ast.walk(lifespan)
            if isinstance(node, ast.Try)
            for handler in [node]
            if any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "unknown_config_keys"
                for call in ast.walk(node)
            )
        ]
        assert guarded, "the key report is unguarded; a broken walker fails the boot"
