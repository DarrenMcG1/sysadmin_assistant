"""The estate's ``docs`` findings reach a sitting here — ``SNAG-DOCS-022``.

What this file is guarding, and why it is a test rather than a check
---------------------------------------------------------------------
estate-manager's ``docs`` check filed
``docs:sysadmin_assistant/HANDOFF.md:next_action_not_startable`` at 13:55 on
2026-09-11 and it reached no sitting in this repository at all.  The entry
says in its own words why no ``check-snag-claims.sh`` entry names it: what
one would drive is *"does anything in this repository's session path read
the estate's findings about it"*, which asserts the **fix**, so ``ok`` would
report *still holds* over a landed closure — ``check_review_schedule_unread``'s
defect.  What is owed is a carrier, and the guard that outlives it is a test
that the carrier exists once it does.  This is that test.

The interesting assertions are not "the notice appears"
--------------------------------------------------------
``scripts/check-estate-docs.sh`` exits silently on every way of not reaching
``:8400``, because the session opened to fix ``:8400`` must not be stalled by
``:8400`` — ``inbox-notice.sh``'s rule, taken with its reason.  That is the
correct direction and it is also the shape that hid three of
``foreign-repo-write-notice.sh``'s defects in succession, each behind the
fail-open exit of the one before.  So what is asserted here is the line
between a silence that is **correct** and a silence that is a **defect**:

* the reader keys on ``sysadmin_assistant`` with an **underscore**, which is
  ``entry.relative`` — the spelling the audit writes.  The register resolves
  the same repository to ``sysadmin-assistant`` with a **hyphen**, and a
  reader keyed on that matches nothing, for ever, and looks exactly like
  health.  Driven as a mutation rather than asserted: see
  ``test_the_hyphen_spelling_reads_zero``;
* an errored ``docs`` check, an absent one, and a finding naming no project
  are each **exit 2**, never exit 0 — ``ports_checked``'s rule, because a run
  in which ``docs`` raised publishes no ``docs`` findings and the obvious
  reader answers "none" off a check that never looked;
* the rung printed is the **producer's**.  A rung this repository has not
  been told about still prints, because translating one here would make this
  tree a second author of a severity estate-manager decided.

The payload shape is not guessed
---------------------------------
``TestTheProducerStillPublishesTheKey`` walks estate-manager's own
``docs.py`` and holds it to the measurement this reader's scope rests on —
every one of its ``Finding(`` sites passes ``detail`` carrying ``project``.
That was 7 of 7 on 2026-09-12, against 0 of 12 for ``pointers`` and 0 of 2
for ``wiring``, which is why the reader is scoped to ``docs`` and not to
every check.  If the estate adds an eighth ``docs`` finding without the key,
that test goes red here rather than this reader going quietly blind.

Not asserted here, and why
---------------------------
The three renderings of ``claude-preflight.sh``'s section — rows, the clean
line, and *"could not be read"* — were driven by hand on 2026-09-12 and are
not re-driven in this suite.  Preflight runs ``check-ops-claims.sh`` and
``check-snag-claims.sh``, which reach PostgreSQL and ``systemctl``; a probe
of it would put seconds into every run of this file to re-measure what its
own two sibling sections already exercise.  What **is** asserted about
preflight is the wiring and the three-way status, which is the half that can
silently regress: ``set -e`` is on, so an uncaptured non-zero status from
this reader would end the banner it was added to inform.
"""

import json
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "scripts" / "check-estate-docs.sh"
PREFLIGHT = ROOT / "scripts" / "claude-preflight.sh"

#: The spelling the audit writes.  Stated once here and derived by the
#: script itself, which is the point: this constant is the *expectation*,
#: not a second producer of the name.
OWN_NAME = "sysadmin_assistant"

#: estate-manager's checkout.  Gated on the **tree**, never on an import —
#: ``importorskip`` would disarm the pin the day the module moved.
#: Overridable for falsification only; the default is the live checkout.
#: The guards in :class:`TestPortsIsRefusedOnAPropertyTheVocabularyCannotMove`
#: assert things about a tree this repository does not own, so the only way
#: to drive them at a producer that has changed is to point them at a copy
#: that has — ``scripts/check-estate-docs.sh``'s own ``ESTATE_PROJECTS_ROOT``
#: idiom, one seam along.  A no-op mutation is not a control.
ESTATE_TREE = Path(
    os.environ.get("ESTATE_TREE_OVERRIDE") or (Path.home() / "projects" / "estate-manager")
)
ESTATE_DOCS_CHECK = ESTATE_TREE / "service" / "estate_service" / "audit" / "checks" / "docs.py"

ESTATE_URL = "http://127.0.0.1:8400"


# ---------------------------------------------------------------------------
# An audit that answers whatever the test needs it to
# ---------------------------------------------------------------------------


@dataclass
class Audit:
    """A stand-in for ``GET :8400/api/audit/findings``."""

    base_url: str = ""
    status: int = 200
    body: str = "{}"
    #: Seconds to stall before answering.  Only the clock test sets it, and
    #: it is the one case where the assertion is about the wall clock rather
    #: than about the presence of a flag — ``--max-time`` is a request in
    #: exactly the way ``-ngl 99`` is.
    delay: float = 0.0
    paths: list[str] = field(default_factory=list)


def _serve(audit: Audit) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            audit.paths.append(self.path)
            if audit.delay:
                time.sleep(audit.delay)
            payload = audit.body.encode()
            try:
                self.send_response(audit.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                # The client gave up on the clock.  That is the case under
                # test, not an error in the fixture.
                pass

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    audit.base_url = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def audit():
    served = Audit()
    server = _serve(served)
    yield served
    server.shutdown()


def finding(
    *,
    project: str = OWN_NAME,
    severity: str = "warn",
    code: str = "next_action_not_startable",
    path: str = "HANDOFF.md",
    standing_days: float = 0.0,
) -> dict:
    """One ``docs`` finding, shaped as the live route serves it.

    The specimen is the real one: the breach filed against this tree at
    13:55 on 2026-09-11, which is the fault this whole carrier exists for.
    """
    detail: dict = {"path": path}
    if project is not None:
        detail["project"] = project
    return {
        "check": "docs",
        "severity": severity,
        "subject": f"{project}/{path}" if project else path,
        "summary": f"{project} next action names a date the document does not declare",
        "fingerprint": f"docs:{project}/{path}:{code}",
        "detail": detail,
        "observed_at": "2026-09-12T15:16:23.405416+00:00",
        "first_seen_at": "2026-09-11T13:55:00.000000+00:00",
        "standing_days": standing_days,
        "runs_observed": 3,
        "age_truncated": False,
    }


def payload(findings: list[dict], *, docs_status: str | None = "findings") -> str:
    """The envelope round the findings, with the per-check summary in it.

    ``docs_status`` is ``None`` for a run that reports no ``docs`` check at
    all — a distinguishable fault from one that errored, and the same answer.
    """
    checks: dict = {}
    if docs_status is not None:
        checks["docs"] = {
            "status": docs_status,
            "findings": len([f for f in findings if f["check"] == "docs"]),
            "error": "registry unreadable" if docs_status == "error" else None,
            "inputs": {},
        }
    return json.dumps(
        {
            "generated_at": "2026-09-12T15:16:23.405416+00:00",
            "run": {"verdict": "findings", "checks": checks},
            "findings": findings,
        }
    )


def run_reader(audit: Audit, *, reader: Path = READER, env: dict | None = None):
    environ = dict(os.environ)
    environ["ESTATE_BASE_URL"] = audit.base_url
    environ.setdefault("ESTATE_PROJECTS_ROOT", str(Path.home() / "projects"))
    environ.update(env or {})
    return subprocess.run(
        ["bash", str(reader)], capture_output=True, text=True, env=environ, timeout=30
    )



def _findings_without_project(module: Path) -> tuple[int, list[int]]:
    """``(how many Finding( there are, the lines of those lacking the key)``.

    An AST walk rather than a ``grep`` for ``"project":``, because the
    string appears in this repository's sibling checks inside summaries and
    docstrings — a name-keyed sweep answers about the module and not about
    the constructions, which is the distinction ``check_markers`` rule 1 and
    ``document_claims.tray_consumption`` each had to learn the hard way.
    """
    import ast

    tree = ast.parse(module.read_text())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Finding"
    ]
    missing: list[int] = []
    for node in calls:
        detail = next((kw.value for kw in node.keywords if kw.arg == "detail"), None)
        keys: list[str] = []
        if isinstance(detail, ast.Dict):
            keys = [k.value for k in detail.keys if isinstance(k, ast.Constant)]
        if "project" not in keys:
            missing.append(node.lineno)
    return len(calls), missing


def _severity_literals(tree_root: Path) -> dict[str, str]:
    """``{"SEVERITY_BREACH": "breach", …}``, read from the producer.

    Resolved by AST out of ``audit/finding.py`` rather than written down
    here, because the rung a code carries is the producer's statement and a
    second copy of it is free to drift — ``max_priority_for`` against
    ``PRIORITY_MAP``'s rule, across a repository boundary.  Parsed rather
    than imported for :class:`TestTheProducerStillPublishesTheKey`'s reason:
    an import disarms the pin on the day the module moves.
    """
    import ast

    module = tree_root / "service" / "estate_service" / "audit" / "finding.py"
    out: dict[str, str] = {}
    for node in ast.walk(ast.parse(module.read_text())):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.startswith("SEVERITY_"):
                out[target.id] = node.value.value
    return out


def _finding_sites(module: Path, severities: dict[str, str]) -> list[dict]:
    """Every ``Finding(`` in *module* as ``{line, code, severity, keys}``.

    The sibling of :func:`_findings_without_project`, and it exists because
    that one answers a **cardinality** — how many sites lack the key — and
    the scope decision in ADR-0013 turns on *which code* carries *which
    rung*.  A count cannot tell a breach that names a project (which
    already arrives here) from a warn that names none (which would be read
    blind), and those are the two facts that decide it.
    """
    import ast

    tree = ast.parse(module.read_text())
    sites: list[dict] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Finding"
        ):
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        code = kw.get("code")
        severity = kw.get("severity")
        detail = kw.get("detail")
        sites.append(
            {
                "line": node.lineno,
                "code": code.value if isinstance(code, ast.Constant) else None,
                "severity": (
                    severities.get(severity.id) if isinstance(severity, ast.Name) else None
                ),
                "keys": (
                    [k.value for k in detail.keys if isinstance(k, ast.Constant)]
                    if isinstance(detail, ast.Dict)
                    else []
                ),
            }
        )
    return sites


# ---------------------------------------------------------------------------
# The carrier exists — the entry's own owed guard
# ---------------------------------------------------------------------------


class TestTheCarrierExists:
    """``SNAG-DOCS-022``'s closure, asserted where it cannot report itself.

    The entry is explicit that no ``check-snag-claims.sh`` check can name it,
    because such a check asserts the fix and would report *still holds* over
    a landed closure.  These four assertions are what is owed instead.
    """

    def test_the_reader_exists_and_is_executable(self):
        assert READER.exists(), (
            "SNAG-DOCS-022's carrier is gone.  The estate files findings about "
            "this repository's documents and, without this, nothing in the "
            "session path reads them."
        )
        assert os.access(READER, os.X_OK)

    def test_preflight_invokes_it(self):
        """The script every session is required to run first must call it.

        A reader nothing calls is the register before ``inbox-notice.sh``:
        live, correct, and inert.
        """
        src = PREFLIGHT.read_text()
        assert "check-estate-docs.sh" in src, (
            "claude-preflight.sh no longer reads the estate's findings about "
            "this repository (SNAG-DOCS-022)."
        )

    def test_preflight_captures_the_status_rather_than_letting_it_propagate(self):
        """``set -e`` is on, so an uncaptured non-zero ends the banner.

        This reader exits non-zero in its ordinary working state — 1 when
        there are findings, 2 whenever the estate is unreachable — so the
        capture is not defensive tidiness.  Without it, a session opened
        while ``:8400`` is down gets no preflight at all, which is the
        failure this addition was written to avoid, arriving through the
        addition itself.
        """
        src = PREFLIGHT.read_text()
        invocation = [
            line for line in src.splitlines() if "./scripts/check-estate-docs.sh" in line
        ]
        assert invocation, "preflight does not invoke the reader"
        assert any("|| " in line and "=$?" in line for line in invocation), (
            "preflight invokes the reader without capturing its status; "
            "`set -e` will end the banner the first time the estate is down"
        )

    def test_preflight_tells_the_three_answers_apart(self):
        """0, 1 and 2 must render differently, or the silence becomes a lie.

        Collapsing 2 into 0 is the whole defect this reader is built around
        one level up: *could not be read* served as *none*.
        """
        src = PREFLIGHT.read_text()
        section = src.split("Estate findings about this repository")[1]
        assert 'DOCS_STATUS" -eq 1' in section
        assert 'DOCS_STATUS" -eq 0' in section
        assert "could not be read" in section
        assert "not the same as 'none'" in section


# ---------------------------------------------------------------------------
# The spelling — the single mistake that ships green
# ---------------------------------------------------------------------------


class TestTheSubjectFilterUsesTheAuditsSpelling:
    """The audit writes an underscore; the register resolves to a hyphen.

    Measured 2026-09-12 against the live register: ``receiver`` declared
    ``sysadmin_assistant`` resolves to ``sysadmin-assistant``.  The audit
    performs no such folding — it keys on ``entry.relative``, which is the
    directory path — so the two spellings are not interchangeable and only
    one of them ever appears in a ``docs`` finding.
    """

    def test_a_finding_about_this_repository_is_read(self, audit):
        audit.body = payload([finding()])
        result = run_reader(audit)
        assert result.returncode == 1
        assert "next_action_not_startable" in result.stdout

    def test_the_hyphen_spelling_reads_zero(self, audit):
        """The mutation, driven rather than described.

        A finding keyed the way the *register* spells this repository is
        invisible to a reader keyed the way the *audit* does — and the
        reverse, which is the direction that would ship.  Exit 0 and empty
        output: indistinguishable from health, for ever.
        """
        audit.body = payload([finding(project="sysadmin-assistant")])
        result = run_reader(audit)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_another_repositorys_finding_is_not_ours(self, audit):
        """``ml/Athenaeum`` is the live population and is not this tree.

        A reader that reported it would make this repository a second
        speaker for a fault whose owner is named in the finding.
        """
        audit.body = payload([finding(project="ml/Athenaeum")])
        result = run_reader(audit)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_the_name_is_derived_from_the_checkout_not_written_down(self, tmp_path, audit):
        """Driven from a checkout with a different name.

        A literal would be the hyphen the day somebody copied it out of a
        ``curl`` they had just run.  This proves the name comes from the
        filesystem the way ``entry.relative`` does.
        """
        projects = tmp_path / "projects"
        elsewhere = projects / "other_repo"
        (elsewhere / "scripts").mkdir(parents=True)
        shutil.copy(READER, elsewhere / "scripts" / READER.name)
        subprocess.run(
            ["git", "-c", "init.defaultBranch=main", "init", "-q", str(elsewhere)],
            check=True,
            capture_output=True,
        )

        audit.body = payload([finding(project="other_repo"), finding(project=OWN_NAME)])
        result = run_reader(
            audit,
            reader=elsewhere / "scripts" / READER.name,
            env={"ESTATE_PROJECTS_ROOT": str(projects)},
        )
        assert result.returncode == 1
        assert "other_repo" in result.stdout
        assert OWN_NAME not in result.stdout

    def test_a_nested_checkout_keys_on_its_relative_path(self, tmp_path, audit):
        """``ml/Athenaeum`` is a real nested repository, so this shape is live.

        The registry walks to depth 2 and ``entry.relative`` carries the
        separator.  A basename-only derivation would key on ``Athenaeum``
        and read zero — the hyphen defect with a different spelling.
        """
        projects = tmp_path / "projects"
        nested = projects / "ml" / "Athenaeum"
        (nested / "scripts").mkdir(parents=True)
        shutil.copy(READER, nested / "scripts" / READER.name)
        subprocess.run(
            ["git", "-c", "init.defaultBranch=main", "init", "-q", str(nested)],
            check=True,
            capture_output=True,
        )

        audit.body = payload([finding(project="ml/Athenaeum")])
        result = run_reader(
            audit,
            reader=nested / "scripts" / READER.name,
            env={"ESTATE_PROJECTS_ROOT": str(projects)},
        )
        assert result.returncode == 1
        assert "ml/Athenaeum" in result.stdout


# ---------------------------------------------------------------------------
# Fail open — and the line between a correct silence and a defect
# ---------------------------------------------------------------------------


class TestItFailsOpen:
    """``:8400`` being down must not stall the session opened to fix ``:8400``.

    Every one of these is exit 2 with nothing on stdout.  The status is what
    keeps the silence honest: preflight renders 2 as *could not be read*, so
    a blind reading never reaches the reader as *none*.
    """

    def test_a_refused_connection_is_silent(self, audit):
        audit.base_url = "http://127.0.0.1:9"
        result = run_reader(audit)
        assert result.returncode == 2
        assert result.stdout.strip() == ""

    def test_a_bad_status_is_silent(self, audit):
        audit.status = 500
        audit.body = payload([finding()])
        result = run_reader(audit)
        assert result.returncode == 2
        assert result.stdout.strip() == ""

    def test_a_body_that_is_not_the_audits_is_silent(self, audit):
        audit.body = "<html>gateway</html>"
        result = run_reader(audit)
        assert result.returncode == 2
        assert result.stdout.strip() == ""

    def test_a_findings_key_that_is_not_a_list_is_silent(self, audit):
        audit.body = json.dumps({"findings": {"docs": 1}, "run": {"checks": {}}})
        result = run_reader(audit)
        assert result.returncode == 2
        assert result.stdout.strip() == ""

    def test_without_jq_it_is_silent(self, audit, tmp_path):
        """Measured by emptying ``PATH`` of it, not by reading the guard.

        ``jq`` does every projection in this script, so its absence is the
        one dependency failure that cannot be worked around.
        """
        audit.body = payload([finding()])
        stub = tmp_path / "bin"
        stub.mkdir()
        for tool in ("curl", "bash", "git", "dirname", "basename", "date"):
            found = shutil.which(tool)
            if found:
                (stub / tool).symlink_to(found)
        result = subprocess.run(
            ["bash", str(READER)],
            capture_output=True,
            text=True,
            env={
                "PATH": str(stub),
                "HOME": os.environ.get("HOME", ""),
                "ESTATE_BASE_URL": audit.base_url,
                "ESTATE_PROJECTS_ROOT": str(Path.home() / "projects"),
            },
            timeout=30,
        )
        assert result.returncode == 2
        assert result.stdout.strip() == ""

    def test_the_hard_clock_is_measured_on_the_wall_clock(self, audit):
        """``--max-time`` is a request in exactly the way ``-ngl 99`` is.

        Asserting the flag is present asserts that somebody typed it.  This
        asserts that a hanging estate does not hold up the banner, which is
        the property the flag is there to buy.
        """
        audit.delay = 10.0
        audit.body = payload([finding()])
        started = time.monotonic()
        result = run_reader(audit, env={"ESTATE_DOCS_TIMEOUT": "1"})
        elapsed = time.monotonic() - started
        assert result.returncode == 2
        assert result.stdout.strip() == ""
        assert elapsed < 5.0, f"the hard clock did not bite: {elapsed:.1f}s"


# ---------------------------------------------------------------------------
# Blind is not clean
# ---------------------------------------------------------------------------


class TestBlindIsNotClean:
    """``ports_checked``'s rule, at the size of a check summary.

    A run whose ``docs`` check raised publishes **no** ``docs`` findings.  The
    obvious reader answers "none for this repository" off a check that never
    looked, which is zero-because-blind served as zero-because-clean — and it
    is the exact shape ``SNAG-DOCS-022`` is about, one level down.
    """

    def test_an_errored_docs_check_is_not_a_clean_read(self, audit):
        audit.body = payload([], docs_status="error")
        result = run_reader(audit)
        assert result.returncode == 2

    def test_an_absent_docs_check_is_not_a_clean_read(self, audit):
        """A run that did not include ``docs`` at all.

        Distinguishable from an error at the producer and the same answer
        here: this run says nothing about documents, which is not the same
        fact as there being nothing to say.
        """
        audit.body = payload([], docs_status=None)
        result = run_reader(audit)
        assert result.returncode == 2

    def test_an_ok_docs_check_with_no_findings_is_a_clean_read(self, audit):
        """The discriminating half.  Without it the class above is vacuous —
        a reader that answered 2 to everything would pass every test in it.
        """
        audit.body = payload([], docs_status="ok")
        result = run_reader(audit)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_a_finding_naming_no_project_is_counted_not_dropped(self, audit):
        """It can neither be claimed as ours nor set aside as anyone's.

        Empty population by the producer's construction — see
        ``TestTheProducerStillPublishesTheKey`` — which is why this branch is
        the guard against that stopping being true rather than a case anyone
        has seen.
        """
        audit.body = payload([finding(project=None)])
        result = run_reader(audit)
        assert result.returncode == 2
        assert "name no project" in result.stdout

    def test_a_findings_check_with_only_other_repositories_is_clean(self, audit):
        """The estate's live state on the day this shipped, asserted as clean.

        Two ``docs`` findings stood, both ``ml/Athenaeum``'s.  The reader must
        exit 0 on that — it is a real read of a real run, and reporting 2
        would make every ordinary morning look like an outage.
        """
        audit.body = payload(
            [finding(project="ml/Athenaeum"), finding(project="ml/Athenaeum", path="docs/adr")]
        )
        result = run_reader(audit)
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# The rung is the producer's
# ---------------------------------------------------------------------------


class TestTheRungIsTheProducers:
    """A ``warn`` about our handoff is advisory where a ``breach`` is not.

    That judgement is estate-manager's, so the word is theirs and this
    repository adds only colour — ``judge_attention``'s deference to a
    nudge's rung, at the size of a word.
    """

    @pytest.mark.parametrize("rung", ["breach", "warn", "info"])
    def test_each_published_rung_is_printed_verbatim(self, audit, rung):
        audit.body = payload([finding(severity=rung)])
        result = run_reader(audit)
        assert result.returncode == 1
        assert result.stdout.startswith(rung + " ")

    def test_a_rung_this_repository_has_not_been_told_about_still_prints(self, audit):
        """Fail open, at the size of a severity.

        The estate may add a rung; a reader that dropped what it did not
        recognise would go silent about the loudest thing it had ever been
        sent.
        """
        audit.body = payload([finding(severity="catastrophe")])
        result = run_reader(audit)
        assert result.returncode == 1
        assert "catastrophe" in result.stdout

    def test_preflight_does_not_strip_the_rung(self):
        """Where this section departs from its two siblings in that file.

        ``check-ops-claims.sh`` and ``check-snag-claims.sh`` emit
        ``ok``/``no``/``??`` — verdict tokens preflight owns, which it strips
        because the content is what follows.  Here the first word is the
        producer's severity and is the thing the row exists to carry.  The
        first draft stripped it, and only rendering the banner said so.
        """
        src = PREFLIGHT.read_text()
        section = src.split("Estate findings about this repository")[1]
        assert "line#breach" not in section
        assert "line#warn" not in section
        assert "line#info" not in section

    def test_the_row_carries_the_fingerprint_and_the_standing_days(self, audit):
        """Printed because the producer publishes them, and judged by nothing.

        ``standing_days`` tells a sitting whether this is new; turning it
        into a deadline would be ageing another repository's finding, which
        ``inbox-notice.sh`` refuses for its own payload and for its reason.
        """
        audit.body = payload([finding(standing_days=17.7)])
        result = run_reader(audit)
        assert "docs:sysadmin_assistant/HANDOFF.md:next_action_not_startable" in result.stdout
        assert "17.7" in result.stdout


# ---------------------------------------------------------------------------
# The producer's half of the seam
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not ESTATE_DOCS_CHECK.exists(),
    reason=f"estate-manager's checkout ({ESTATE_DOCS_CHECK}) is not on this box",
)
class TestTheProducerStillPublishesTheKey:
    """The measurement this reader's whole scope rests on.

    ``docs`` is the only one of estate-manager's check modules for
    which **every** ``Finding`` carries ``detail["project"]`` — 7 of 7 on
    2026-09-12, against 0 of 12 for ``pointers``, 0 of 2 for ``wiring`` and 2
    of 9 for ``consumers``.  That is why the reader is keyed on that field
    and scoped to that check.

    *The module count is retired rather than refreshed* (``SNAG-DOCS-030``).
    **The only one** is already total, so the cardinal added nothing the
    word did not carry; the per-check figures beside it stay, because each
    is stamped with the day it was taken and a dated measurement cannot
    drift where a live cardinality can.

    Gated on the **tree**, never on an import: ``importorskip`` would disarm
    the pin on the day the module moved, which is the day it matters.
    """

    def test_every_docs_finding_carries_the_project_key(self):
        total, missing = _findings_without_project(ESTATE_DOCS_CHECK)
        assert total, "no Finding( construction found — has the check moved?"
        assert not missing, (
            "estate-manager's docs check now builds a Finding without "
            f"detail['project'] at {ESTATE_DOCS_CHECK}:{missing}. "
            "scripts/check-estate-docs.sh keys on that field, so those "
            "findings are invisible to this repository's session path — "
            "SNAG-DOCS-022's carrier has a blind spot it cannot report."
        )

    @pytest.mark.parametrize("other", ["pointers", "wiring", "consumers"])
    def test_the_detector_can_be_seen_to_fail(self, other):
        """Driven at the modules that must trip it.

        ``test_autogenerate_config.py``'s idiom, and the reason it is needed
        here: the assertion above is ``assert not missing``, which a walker
        that finds nothing at all satisfies perfectly.  A detector proved
        only against a clean subject is indistinguishable from one that has
        stopped looking.

        These three were also read, until 2026-09-14, as *the* measurement
        scoping the reader: if one started passing, the refusal to widen
        past ``docs`` had lost its reason.  **That inference is retired and
        the assertion is kept.**  estate-manager re-took the count over all
        1,666 stored findings (message ``a9ee6305``) and refuted the
        conclusion for ``ports`` — 803 of 929, every claimant-naming code at
        100 % — while this repository's own walker had aged in two days.
        A key's presence is necessary for a project-keyed reader and it was
        never sufficient, which is what ADR-0013 records and
        :class:`TestPortsIsRefusedOnAPropertyTheVocabularyCannotMove` pins.

        So one of these starting to pass is still **news** — it says the
        producer's vocabulary moved under a scope decision — but it is no
        longer, on its own, a reason to widen anything.
        """
        module = ESTATE_DOCS_CHECK.parent / f"{other}.py"
        if not module.exists():
            pytest.skip(f"{other}.py is not in estate-manager's checkout")
        total, missing = _findings_without_project(module)
        assert total, f"no Finding( construction found in {other}.py"
        assert missing, (
            f"every Finding in estate-manager's {other} check now carries "
            "detail['project'].  That is the key scripts/check-estate-docs.sh "
            "needs, so the measured reason for scoping the reader to `docs` "
            "(SNAG-DOCS-022) no longer holds for this check — re-measure and "
            "decide whether to widen."
        )


# ---------------------------------------------------------------------------
# Why the reader is not pointed at `ports` — ADR-0013
# ---------------------------------------------------------------------------


#: The two codes ADR-0013's refusal rests on, named because they are the
#: producer's vocabulary and cannot be derived from anything on this side.
#: Both had filed **nothing** across estate-manager's 430 audit runs, which
#: is why neither is visible to any count over ``audit_findings`` — theirs
#: (message ``a9ee6305``) or the census this reader used to carry.
PORTS_OVERLAP_CODE = "claimed_by_an_unregistered_tree"
PORTS_BLIND_CODE = "claimed_by_more_than_one_row"


@pytest.mark.skipif(
    not ESTATE_DOCS_CHECK.exists(),
    reason=f"estate-manager's checkout ({ESTATE_DOCS_CHECK.parent}) is not on this box",
)
class TestPortsIsRefusedOnAPropertyTheVocabularyCannotMove:
    """The scope decision, pinned at the property rather than at a count.

    ``scripts/check-estate-docs.sh`` reads ``docs`` and nothing else.  It
    used to justify that with a census of the producer — *``docs`` is the
    only check whose findings all carry ``detail.project``* — and
    estate-manager refuted the **conclusion** of that census over all 1,666
    stored findings (``a9ee6305``): ``ports`` publishes the key on 803 of
    929, and on 100 % of every code that has a claimant to name.

    They are right, and this repository's own figure had aged in two days —
    ``ports  4 findings, 3`` on 2026-09-12 against **6 sites, 4** once their
    ADR-0166 and ADR-0168 landed.  A census of a vocabulary is the wrong
    instrument to hang a scope on; their ADR-0171 measured how fast that
    vocabulary moves.

    So the refusal stands on a property instead, and the property is that a
    project-keyed reader over ``ports`` is wrong in **both directions at
    once**:

    * one code is at the rung this repository **already judges**, and
      carries the key — so the reader would say a second time what the tray
      already says (the second-owner defect);
    * one code **names claimants without publishing the key** — so the
      reader is blind to it and cannot say so (``ports_checked``'s rule).

    Neither is reachable by counting filings, because neither has ever
    filed.  That is the whole of why this class reads their **source**.
    """

    def _sites(self) -> list[dict]:
        return _finding_sites(
            ESTATE_DOCS_CHECK.parent / "ports.py", _severity_literals(ESTATE_TREE)
        )

    @pytest.mark.premise
    def test_the_walker_reads_their_codes_and_rungs_or_nothing_below_is_evidence(self):
        """Every assertion below believes something *about* a site.

        A walker that resolved no code, or no rung, would report an empty
        vocabulary and satisfy the negative half of this class perfectly —
        ``SNAG-TRAY-010``'s lesson, and the same gate the live half opens
        with.  ``severity`` is resolved through their own
        ``SEVERITY_* = "…"`` assignments, so a rename there shows up here as
        ``None`` rather than as a silent pass.
        """
        sites = self._sites()
        assert sites, "no Finding( construction found — has the ports check moved?"
        assert all(s["code"] for s in sites), (
            f"a ports Finding carries no literal code: {[s for s in sites if not s['code']]}"
        )
        assert all(s["severity"] for s in sites), (
            "a ports Finding's rung did not resolve against their "
            f"SEVERITY_* constants: {[s for s in sites if not s['severity']]}"
        )

    def test_a_code_at_the_rung_we_already_judge_carries_the_key(self):
        """Direction one: the reader would give one fault two speakers.

        Composed rather than restated — the rung comes from this
        repository's :data:`JUDGED_AUDIT_CHECKS`, which is what actually
        decides whether a finding arrives here, and the key comes from their
        source.  Asserting ``"breach"`` on both sides would pin a coincidence
        instead of the conjunction that does the work.
        """
        from sysadmin.estate.judgements import JUDGED_AUDIT_CHECKS, PORTS_CHECK

        judged_rung = JUDGED_AUDIT_CHECKS[PORTS_CHECK]
        overlap = [
            s
            for s in self._sites()
            if s["severity"] == judged_rung and "project" in s["keys"]
        ]
        assert overlap, (
            f"no ports code is now both at the rung this repository judges "
            f"({judged_rung!r}) and carrying detail['project'].  ADR-0013's first "
            "reason for keeping scripts/check-estate-docs.sh off `ports` was that "
            f"{PORTS_OVERLAP_CODE!r} is exactly that, so a reader here would repeat "
            "what the tray already speaks.  If that is no longer true, re-read "
            "ADR-0013 §4 before widening anything — it is news, not a failure."
        )
        assert any(s["code"] == PORTS_OVERLAP_CODE for s in overlap), (
            f"{PORTS_OVERLAP_CODE!r} is no longer the code carrying that "
            f"conjunction; it is now {[s['code'] for s in overlap]}.  ADR-0013 names "
            "the code, so the record has to move with it."
        )

    def test_a_code_that_names_claimants_publishes_none_under_the_key(self):
        """Direction two: the reader would be blind and unable to say so.

        ``claimed_by_more_than_one_row`` names its claimants one level down,
        in ``detail["rows"][].project``.  A reader keyed on
        ``detail.project`` matches nothing and reports *none for us*, which
        is zero-because-blind served as zero-because-clean — and it is the
        one ports code that can name this repository without naming a port
        this repository holds.

        estate-manager's sentence is quantified over findings **ever
        filed**, and this code has filed none, so it sits outside their
        quantifier rather than contradicting it.
        """
        blind = [s for s in self._sites() if s["code"] == PORTS_BLIND_CODE]
        assert blind, (
            f"{PORTS_BLIND_CODE!r} is gone from estate-manager's ports check. "
            "ADR-0013 §5 rests on it, so the record has to move with it."
        )
        site = blind[0]
        assert "project" not in site["keys"], (
            f"{PORTS_BLIND_CODE!r} now publishes detail['project'] "
            f"(keys={site['keys']}).  The blind half of ADR-0013's refusal has lost "
            "its reason — re-measure both halves before widening the reader."
        )
        assert len(site["keys"]) > 1, (
            f"{PORTS_BLIND_CODE!r} now carries nothing but {site['keys']}, so it no "
            "longer names claimants at all and this is no longer a blind spot."
        )

    def test_docs_trips_neither_which_is_the_reason_docs_is_the_one_read(self):
        """The control, and it is the positive case rather than a stand-in.

        A class made only of *this producer breaks the reader* assertions is
        satisfied by a walker that flags everything.  ``docs`` is walked by
        the same code and must come back clean on both predicates — no
        blind spot, because 9 of 9 of its sites carry the key, and no
        overlap, because ``docs`` is **not** in
        :data:`JUDGED_AUDIT_CHECKS` at all and so nothing about it arrives
        here twice.

        That second half is the discrimination the first draft of this test
        missed: ``docs`` does file at ``breach`` and does carry the key, so a
        predicate reading *breach + project* alone flags it too.  What
        separates the two checks is membership of the judged set, which is
        why the assertion above is a conjunction and not a scan for a rung.
        """
        from sysadmin.estate.judgements import JUDGED_AUDIT_CHECKS

        assert "docs" not in JUDGED_AUDIT_CHECKS, (
            "`docs` has entered the judged set, so its findings now arrive here "
            "as alerts as well as through scripts/check-estate-docs.sh — which is "
            "the second-owner defect ADR-0013 refuses `ports` for, arriving on the "
            "one check the reader does read."
        )
        sites = _finding_sites(ESTATE_DOCS_CHECK, _severity_literals(ESTATE_TREE))
        assert sites, "no Finding( construction found in docs.py"
        assert not [s for s in sites if "project" not in s["keys"]], (
            "a docs finding now omits detail['project'], so the reader has a blind "
            "spot on the one check it reads."
        )


# ---------------------------------------------------------------------------
# Live half — the only thing that can catch the producer
# ---------------------------------------------------------------------------


def _estate_available() -> bool:
    try:
        import httpx

        return httpx.get(f"{ESTATE_URL}/api/health", timeout=2.0).status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _estate_available(), reason=f"estate-manager ({ESTATE_URL}) unreachable")
class TestTheLiveAuditStillSpellsItThisWay:
    """The witness for the one mistake that would ship green.

    The recorded half above cannot catch a producer that starts keying
    ``detail.project`` on the registry **id** rather than on the path — the
    field would still be present and this reader would read zero for ever.
    What discriminates is that the published value resolves to a directory,
    which the hyphenated id does not.

    It asserts over ``ml/Athenaeum``'s live findings rather than over this
    repository's, because this repository's population is **zero** — its own
    breach was repaired on 2026-09-12, which is exactly why a witness keyed
    on our own row would have nothing to say.
    """

    def _body(self) -> dict:
        import httpx

        return httpx.get(f"{ESTATE_URL}/api/audit/findings", timeout=10.0).json()

    def _findings(self) -> list[dict]:
        return [f for f in self._body().get("findings", []) if f.get("check") == "docs"]

    @pytest.mark.premise
    def test_the_premises_hold_or_nothing_below_means_anything(self):
        """The estate answered, and its ``docs`` check actually ran.

        Both witnesses below believe a **negative** — *no finding names a
        project that is not a directory*, and *no docs finding lacks a
        project* — and an audit that has never run satisfies each of them
        perfectly, off an empty list.  The skip inside the first is the same
        hole in smaller form: a box where ``docs`` never ran skips, reads
        green, and has asserted nothing about the producer.

        So the gate is ordered first and named, which is ``SNAG-TRAY-010``'s
        whole lesson: a harness that produced nothing reads exactly like a
        subject that is clean.  It is the same distinction
        ``scripts/check-estate-docs.sh`` draws with exit 2, asserted here
        against the live producer rather than against a stand-in.
        """
        body = self._body()
        checks = body.get("run", {}).get("checks", {})
        assert checks, "the live audit reports no checks at all — it has not run"
        assert "docs" in checks, (
            "the live audit ran and did not include the `docs` check, so "
            "nothing below is evidence about it"
        )
        assert checks["docs"].get("error") is None, (
            f"the live `docs` check errored ({checks['docs'].get('error')!r}), so "
            "its empty finding list is zero-because-blind"
        )
        assert isinstance(body.get("findings"), list)

    def test_every_docs_finding_names_a_directory_under_the_projects_root(self):
        projects = Path.home() / "projects"
        findings = self._findings()
        if not findings:
            pytest.skip("the live audit holds no docs findings to witness")
        for f in findings:
            project = f.get("detail", {}).get("project")
            assert project, f"a live docs finding names no project: {f.get('fingerprint')}"
            assert (projects / project).is_dir(), (
                f"the audit published detail.project={project!r}, which is not a "
                "directory under the projects root.  The reader in "
                "scripts/check-estate-docs.sh derives this repository's name the "
                "same way; if the producer has moved to registry ids, that reader "
                "now matches nothing and reports health (SNAG-DOCS-022)."
            )

    def test_this_repositorys_own_spelling_is_the_underscore_one(self):
        """Driven at the register, which folds, and the audit, which does not.

        The register resolving ``sysadmin_assistant`` to
        ``sysadmin-assistant`` is what makes the hyphen reachable by a
        careless hand at all — so it is asserted here rather than left as
        prose in the reader's docstring.
        """
        import httpx

        body = httpx.get(
            f"{ESTATE_URL}/api/estate/messages",
            params={"receiver": OWN_NAME, "state": "open"},
            timeout=10.0,
        ).json()
        resolved = body.get("filter", {}).get("receiver", {})
        assert resolved.get("resolved") is True
        assert resolved.get("resolved_to") != OWN_NAME, (
            "the register no longer folds this repository's two spellings, so "
            "the trap SNAG-DOCS-022 names may have gone — re-measure before "
            "relaxing the reader's derivation"
        )
        assert (Path.home() / "projects" / OWN_NAME).is_dir()
