"""Tests for the project registry (Phase 1)."""

from pathlib import Path

import pytest
import yaml

from sysadmin.registry import (
    MANIFEST_NAME,
    Decision,
    DuplicateProjectIdError,
    ManifestError,
    ProjectManifest,
    UnknownProjectError,
    derive_category,
    derive_id,
    discover_repositories,
    effective_status,
    is_repository,
    load_registry,
    read_manifest,
    should_prune,
)
from sysadmin.registry.registry import (
    FINDING_PROVISIONAL_COLLISION,
    FINDING_UNDECLARED,
)


def make_repo(root: Path, relative: str, manifest: dict | str | None = None) -> Path:
    """Create a repository directory, optionally with a manifest."""
    path = root / relative
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir(exist_ok=True)
    if isinstance(manifest, str):
        (path / MANIFEST_NAME).write_text(manifest, encoding="utf-8")
    elif manifest is not None:
        (path / MANIFEST_NAME).write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
    return path


def declared(project_id: str, name: str, **extra) -> dict:
    return {"schema": 1, "id": project_id, "name": name, **extra}


# ── discovery ────────────────────────────────────────────────────


class TestDiscovery:
    def test_git_directory_makes_a_repository(self, tmp_path):
        (tmp_path / "thing").mkdir()
        assert not is_repository(tmp_path / "thing")
        (tmp_path / "thing" / ".git").mkdir()
        assert is_repository(tmp_path / "thing")

    def test_manifest_alone_makes_a_repository(self, tmp_path):
        path = tmp_path / "declared-only"
        path.mkdir()
        (path / MANIFEST_NAME).write_text("schema: 1\n", encoding="utf-8")
        assert is_repository(path)

    def test_finds_repositories_at_depth_two(self, tmp_path):
        make_repo(tmp_path, "Alfred")
        make_repo(tmp_path, "apps/SportsAnalyser")
        found = discover_repositories(tmp_path, depth=2)
        assert {p.name for p in found} == {"Alfred", "SportsAnalyser"}

    def test_depth_one_does_not_enter_categories(self, tmp_path):
        make_repo(tmp_path, "Alfred")
        make_repo(tmp_path, "apps/SportsAnalyser")
        found = discover_repositories(tmp_path, depth=1)
        assert {p.name for p in found} == {"Alfred"}

    def test_depth_three_reaches_a_nested_repository(self, tmp_path):
        make_repo(tmp_path, "work/assignment/thing")
        assert discover_repositories(tmp_path, depth=2) == []
        assert len(discover_repositories(tmp_path, depth=3)) == 1

    def test_repository_is_never_descended_into(self, tmp_path):
        make_repo(tmp_path, "outer")
        make_repo(tmp_path, "outer/vendored")
        found = discover_repositories(tmp_path, depth=3)
        assert [p.name for p in found] == ["outer"]

    @pytest.mark.parametrize(
        "name",
        ["node_modules", "__pycache__", ".venv", "venv", "build", "dist",
         ".next", ".nuxt", "target", ".godot"],
    )
    def test_prune_list(self, name):
        assert should_prune(name)

    def test_prunes_bare_mirror_directories(self, tmp_path):
        make_repo(tmp_path, "real")
        make_repo(tmp_path, ".backups/real.git")
        make_repo(tmp_path, "mirrors/other.git")
        found = discover_repositories(tmp_path, depth=3)
        assert [p.name for p in found] == ["real"]

    def test_hidden_directories_are_skipped(self, tmp_path):
        make_repo(tmp_path, "real")
        make_repo(tmp_path, ".backups/snapshot")
        found = discover_repositories(tmp_path, depth=3)
        assert [p.name for p in found] == ["real"]

    def test_symlinked_directories_are_skipped(self, tmp_path):
        make_repo(tmp_path, "real")
        (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
        found = discover_repositories(tmp_path, depth=2)
        assert [p.name for p in found] == ["real"]

    def test_unreadable_root_returns_empty(self, tmp_path):
        assert discover_repositories(tmp_path / "missing", depth=2) == []


class TestDerivation:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("SportsAnalyser", "sportsanalyser"),
            ("BSL-Translator", "bsl-translator"),
            ("sysadmin_assistant", "sysadmin-assistant"),
            ("PersonalAssistant-auto", "personalassistant-auto"),
            ("--odd--", "odd"),
            ("...", "unnamed"),
        ],
    )
    def test_derive_id(self, name, expected):
        assert derive_id(name) == expected

    def test_derive_category(self, tmp_path):
        assert derive_category(tmp_path / "apps" / "thing", tmp_path) == "apps"
        assert derive_category(tmp_path / "thing", tmp_path) is None


# ── manifest schema ──────────────────────────────────────────────


class TestManifest:
    def test_minimal_manifest_is_undeclared_not_active(self):
        manifest = ProjectManifest.model_validate(declared("thing", "Thing"))
        assert manifest.status == "undeclared"

    def test_full_manifest(self):
        manifest = ProjectManifest.model_validate({
            "schema": 1,
            "id": "sports-analyser",
            "name": "SportsAnalyser",
            "category": "apps",
            "status": "dormant",
            "summary": "Sports data pipeline and analysis frontend",
            "supersedes": [],
            "tags": [],
            "alert_threshold": None,
            "decisions": [
                {
                    "date": "2026-08-06",
                    "change": "active -> dormant",
                    "reason": "board flagged stalled at 152 days",
                    "note": "endpoints stay monitored",
                }
            ],
        })
        assert manifest.status == "dormant"
        assert manifest.decisions[0].date.isoformat() == "2026-08-06"
        assert isinstance(manifest.decisions[0], Decision)

    def test_idle_nudge_days_defaults_to_the_global_setting(self):
        """A manifest that says nothing takes config.yaml's threshold."""
        manifest = ProjectManifest.model_validate(declared("thing", "Thing"))
        assert manifest.idle_nudge_days is None

    def test_idle_nudge_days_is_separate_from_alert_threshold(self):
        """Health and commitment are different questions (Session 31).

        A long-cycle repository wants a relaxed nudge without also going
        unwatched for a missing README.
        """
        manifest = ProjectManifest.model_validate(
            declared("thing", "Thing") | {"idle_nudge_days": 21, "alert_threshold": 40}
        )
        assert (manifest.idle_nudge_days, manifest.alert_threshold) == (21, 40)

    @pytest.mark.parametrize("bad", [0, -1])
    def test_idle_nudge_days_must_be_at_least_one(self, bad):
        """Zero would nudge on the scan that wrote the action."""
        with pytest.raises(ValueError, match="idle_nudge_days"):
            ProjectManifest.model_validate(
                declared("thing", "Thing") | {"idle_nudge_days": bad}
            )

    def test_unknown_schema_rejected(self):
        with pytest.raises(ValueError, match="unsupported schema"):
            ProjectManifest.model_validate(declared("thing", "Thing") | {"schema": 2})

    @pytest.mark.parametrize(
        "bad_id",
        ["SportsAnalyser", "sports_analyser", "sports--analyser", "-leading",
         "trailing-", "sports analyser", ""],
    )
    def test_id_must_be_kebab_case(self, bad_id):
        with pytest.raises(ValueError):
            ProjectManifest.model_validate(declared(bad_id, "Thing"))

    def test_unknown_status_rejected(self):
        with pytest.raises(ValueError):
            ProjectManifest.model_validate(
                declared("thing", "Thing", status="retired")
            )

    def test_typo_field_is_rejected_not_ignored(self):
        with pytest.raises(ValueError):
            ProjectManifest.model_validate(
                declared("thing", "Thing") | {"statuss": "dormant"}
            )

    def test_supersedes_must_be_kebab_case(self):
        with pytest.raises(ValueError):
            ProjectManifest.model_validate(
                declared("alfred", "Alfred", supersedes=["PersonalAssistant"])
            )

    def test_read_manifest_absent(self, tmp_path):
        assert read_manifest(tmp_path) is None

    def test_read_manifest_bad_yaml(self, tmp_path):
        (tmp_path / MANIFEST_NAME).write_text("id: [unclosed\n", encoding="utf-8")
        with pytest.raises(ValueError, match="unreadable YAML"):
            read_manifest(tmp_path)

    def test_read_manifest_not_a_mapping(self, tmp_path):
        (tmp_path / MANIFEST_NAME).write_text("- a\n- b\n", encoding="utf-8")
        with pytest.raises(ValueError, match="mapping"):
            read_manifest(tmp_path)


# ── effective status ─────────────────────────────────────────────


class TestEffectiveStatus:
    def test_no_manifest_is_undeclared(self, tmp_path):
        assert effective_status(None, tmp_path / "thing", tmp_path) == "undeclared"

    def test_no_manifest_under_archive_is_archived(self, tmp_path):
        path = tmp_path / "archive" / "PersonalAssistant"
        path.mkdir(parents=True)
        assert effective_status(None, path, tmp_path) == "archived"

    def test_declared_status_wins_over_location(self, tmp_path):
        path = tmp_path / "archive" / "thing"
        path.mkdir(parents=True)
        manifest = ProjectManifest.model_validate(
            declared("thing", "Thing", status="active")
        )
        assert effective_status(manifest, path, tmp_path) == "active"

    def test_explicit_undeclared_still_infers_archive(self, tmp_path):
        path = tmp_path / "archive" / "thing"
        path.mkdir(parents=True)
        manifest = ProjectManifest.model_validate(
            declared("thing", "Thing", status="undeclared")
        )
        assert effective_status(manifest, path, tmp_path) == "archived"


# ── the registry ─────────────────────────────────────────────────


class TestLoadRegistry:
    def test_empty_root(self, tmp_path):
        registry = load_registry(tmp_path)
        assert len(registry) == 0
        assert registry.ids == ()

    def test_id_to_path_map(self, tmp_path):
        make_repo(tmp_path, "apps/SportsAnalyser",
                  declared("sports-analyser", "SportsAnalyser", status="dormant"))
        make_repo(tmp_path, "Alfred", declared("alfred", "Alfred", status="active"))
        registry = load_registry(tmp_path)

        assert registry.ids == ("alfred", "sports-analyser")
        assert registry.paths_by_id["sports-analyser"].name == "SportsAnalyser"
        assert registry.resolve("alfred").status == "active"

    def test_undeclared_is_reported_not_defaulted_to_active(self, tmp_path):
        make_repo(tmp_path, "apps/mystery")
        registry = load_registry(tmp_path)

        entry = registry.entries[0]
        assert entry.status == "undeclared"
        assert entry.declared is False
        assert registry.undeclared == (entry,)
        assert registry.declared == ()

    def test_undeclared_id_is_not_resolvable(self, tmp_path):
        make_repo(tmp_path, "apps/SportsAnalyser")
        registry = load_registry(tmp_path)

        assert registry.entries[0].provisional_id == "sportsanalyser"
        assert registry.ids == ()
        assert registry.resolve("sportsanalyser") is None

    def test_undeclared_produces_a_finding(self, tmp_path):
        make_repo(tmp_path, "apps/mystery")
        registry = load_registry(tmp_path)
        kinds = [f.kind for f in registry.findings]
        assert FINDING_UNDECLARED in kinds

    def test_category_derived_when_manifest_omits_it(self, tmp_path):
        make_repo(tmp_path, "apps/daiy", declared("daiy", "daiy"))
        registry = load_registry(tmp_path)
        assert registry.entries[0].category == "apps"

    def test_manifest_category_wins(self, tmp_path):
        make_repo(tmp_path, "apps/daiy", declared("daiy", "daiy", category="ml"))
        registry = load_registry(tmp_path)
        assert registry.entries[0].category == "ml"

    def test_relative_path_is_recorded(self, tmp_path):
        make_repo(tmp_path, "apps/daiy", declared("daiy", "daiy"))
        registry = load_registry(tmp_path)
        assert registry.entries[0].relative == "apps/daiy"


class TestLoadTimeFailures:
    def test_invalid_manifest_raises_at_load(self, tmp_path):
        make_repo(tmp_path, "good", declared("good", "Good"))
        make_repo(tmp_path, "bad", declared("Bad_Id", "Bad"))
        with pytest.raises(ManifestError) as excinfo:
            load_registry(tmp_path)
        assert "kebab-case" in str(excinfo.value)

    def test_every_invalid_manifest_is_reported_at_once(self, tmp_path):
        make_repo(tmp_path, "one", declared("One", "One"))
        make_repo(tmp_path, "two", {"schema": 9, "id": "two", "name": "Two"})
        make_repo(tmp_path, "three", "id: [unclosed\n")
        with pytest.raises(ManifestError) as excinfo:
            load_registry(tmp_path)
        assert len(excinfo.value.problems) == 3

    def test_duplicate_declared_id_raises(self, tmp_path):
        make_repo(tmp_path, "apps/thing", declared("thing", "Thing"))
        make_repo(tmp_path, "ml/thing-again", declared("thing", "Thing Again"))
        with pytest.raises(DuplicateProjectIdError) as excinfo:
            load_registry(tmp_path)
        assert set(excinfo.value.collisions) == {"thing"}
        assert len(excinfo.value.collisions["thing"]) == 2

    def test_colliding_provisional_ids_are_reported_not_raised(self, tmp_path):
        make_repo(tmp_path, "apps/BSL-Translator")
        make_repo(tmp_path, "archive/bsl-translator")
        registry = load_registry(tmp_path)

        collisions = [
            f for f in registry.findings
            if f.kind == FINDING_PROVISIONAL_COLLISION
        ]
        assert [f.subject for f in collisions] == ["bsl-translator"]

    def test_unknown_supersedes_raises_at_load(self, tmp_path):
        make_repo(tmp_path, "Alfred",
                  declared("alfred", "Alfred", supersedes=["personal-assistant"]))
        with pytest.raises(UnknownProjectError) as excinfo:
            load_registry(tmp_path)
        assert excinfo.value.unknown == ["personal-assistant"]

    def test_known_supersedes_loads(self, tmp_path):
        make_repo(tmp_path, "Alfred",
                  declared("alfred", "Alfred", supersedes=["personal-assistant"]))
        make_repo(tmp_path, "archive/PersonalAssistant",
                  declared("personal-assistant", "PersonalAssistant",
                           status="archived"))
        registry = load_registry(tmp_path)
        assert registry.ids == ("alfred", "personal-assistant")

    def test_supersedes_cannot_point_at_an_undeclared_repository(self, tmp_path):
        make_repo(tmp_path, "Alfred",
                  declared("alfred", "Alfred", supersedes=["personalassistant"]))
        make_repo(tmp_path, "archive/PersonalAssistant")
        with pytest.raises(UnknownProjectError):
            load_registry(tmp_path)


class TestReferenceChecking:
    @pytest.fixture
    def registry(self, tmp_path):
        make_repo(tmp_path, "Alfred", declared("alfred", "Alfred", status="active"))
        make_repo(tmp_path, "apps/SportsAnalyser",
                  declared("sports-analyser", "SportsAnalyser", status="dormant"))
        return load_registry(tmp_path)

    def test_require_returns_the_entry(self, registry):
        assert registry.require("alfred", "services.yaml").name == "Alfred"

    def test_require_raises_on_unknown(self, registry):
        with pytest.raises(UnknownProjectError, match="services.yaml"):
            registry.require("nope", "services.yaml")

    def test_error_lists_the_known_ids(self, registry):
        with pytest.raises(UnknownProjectError) as excinfo:
            registry.require("nope", "services.yaml")
        assert excinfo.value.known == ["alfred", "sports-analyser"]

    def test_assert_known_passes(self, registry):
        registry.assert_known(["alfred", "sports-analyser"], "services.yaml")

    def test_assert_known_reports_every_bad_reference_at_once(self, registry):
        with pytest.raises(UnknownProjectError) as excinfo:
            registry.assert_known(
                ["alfred", "nope", "also-nope", "nope"], "services.yaml"
            )
        assert excinfo.value.unknown == ["also-nope", "nope"]

    def test_assert_known_accepts_nothing(self, registry):
        registry.assert_known([], "services.yaml")


class TestLiveEstate:
    """Guards on the manifests this box actually carries.

    Skipped off this machine — they assert about ~/projects, not about the
    repository, and a fixture estate would only re-test the parser.
    """

    @pytest.fixture(scope="class")
    def registry(self):
        try:
            return load_registry("~/projects")
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"estate unavailable: {exc}")

    def test_every_manifest_parses(self, registry):
        if not registry.ids:
            pytest.skip("estate not migrated on this machine")
        assert len(registry.declared) >= 14

    def test_the_reasoning_transfer_is_not_silently_lost(self, registry):
        """projects.yaml's comments were the only record of several
        decisions. If a manifest loses its decisions block, the record is
        gone and nothing else would notice."""
        if not registry.ids:
            pytest.skip("estate not migrated on this machine")
        without = [
            e.id for e in registry.declared
            if e.manifest and not e.manifest.decisions
        ]
        assert without == ["sysadmin-assistant"], (
            "a manifest lost its decisions; the legacy file at "
            "docs/projects-registry-legacy.yaml is the only other copy"
        )

    def test_no_declared_project_is_left_undeclared(self, registry):
        if not registry.ids:
            pytest.skip("estate not migrated on this machine")
        assert all(e.status != "undeclared" for e in registry.declared)
