"""``CLAUDE.md``'s Contract Registry, swept against the routes it indexes.

``SNAG-DOCS-014``.  The section closes by stating that *"the registry
describes only what this service serves or parses, and membership is a
property a test computes"*.  The test it means is
``tests/test_contract_reachability.py``, which walks field annotations and
base classes from every root — a property of the **models**.  Nothing walked
the **routes**, so a route added with no registry row was invisible to the
very mechanism the document named as its guarantee, and measured 2026-09-10
fourteen served ``(method, path)`` pairs had no row.

That is ``SNAG-DOCS-001`` run backwards.  There, fifteen models describing
routes that had left the repository stayed in this table and a reader
concluded this service served them; here a route is served and unlisted, and
it costs the tray, which reads this table to know what shape to parse.

**The membership rule is mechanical, which is the part the entry expected to
be a judgement.**  A route belongs in the registry iff a ``contracts.py``
model is bound to it — as ``response_model=`` on the producer side, or as the
tray's parse on the consumer side.

**Both halves are computed now** (``SNAG-DOCS-017``, closed).  The producer
half is readable straight off ``create_app()``, because FastAPI *stores*
``response_model`` on the route object.  The consumer half has no such
object: the pairing between the URL requested and the class the reply is
handed to exists only as adjacency in a function body, so
:func:`document_claims.tray_consumption` walks it.  Until that existed the
nine ``parse-side only`` and ``serialise-side only`` rows asserted their half
in prose and were believed — measured true 8 of 8, which was the ranking and
not a reason to leave it, since reading a correct population as a settled
class is what mis-ranked ``SNAG-LOG-010``'s parent.

Seven rules, five of them the opposite of the obvious implementation:

1. **The exemption table cannot hide a contract.**  A pinned route is refused
   an entry there, so the list can only ever excuse what the code has already
   left unpinned — ``check_markers`` rule 1's refusal of a marker whose
   deletion retires a check, met from the other side.  Without that clause an
   exemption row is a switch, and "edit the document" silences the guard.

2. **The exemption is read from the document, never held here.**  A list
   living in this module would protect this module's knowledge and leave the
   reader exactly as misled, which is the whole of ``SNAG-DOCS-001``.
   ``routes_by_prefix``' rule: the document supplies the partition and the
   test checks it for *totality*.

3. **Path parameters are normalised, and the normalisation is itself
   measured.**  :func:`document_claims.normalise_path` collapses ``{id}`` and
   ``{alert_id}`` to one spelling; a collapse compares fewer things than it
   believes unless it is injective over the population, so that is a test
   rather than a claim in a docstring.

4. **The content half ships with an empty finding population and says so.**
   Every row's enforcement cell was measured against the box before this
   module existed and was correct 36 of 36 — so
   :class:`TestEveryRowsEnforcementIsTrue` is a regression guard rather than
   a repair, which is worth stating because a green guard nobody has seen
   fail is indistinguishable from one that cannot fail.

5. **Nothing here writes to the document.**  ``ops_claims.py`` rule 6: a
   check that corrects the file it reads becomes a second author of the
   claim.

6. **A name in the tray is not a parse, and that is why this was a second
   sitting rather than a wider grep.**  ``sysadmin_tray/models.py``
   re-exports ``contracts.py`` wholesale, so every model the registry names
   is present under ``sysadmin_tray/`` for reasons unrelated to any route: a
   name-keyed sweep answers *true* for all of them and would have shipped
   green while measuring nothing.  The walk keys on the **call** —
   ``Model.from_dict(resp.json())`` — which is the verb rather than the noun.

7. **The exemption table cannot hide a consumer contract either.**  Rule 1
   refuses an exemption to a route the *producer* pinned; the same clause is
   owed on the other side, or a route the tray parses with a contract could
   be excused from the registry by a document edit.  That direction was
   unreachable before the walk and is what rule 1 was missing rather than a
   new rule.

**What the walk cannot see is stated rather than left silent.**  Four
exemption reasons say *no consumer*, and two of this repository's consumers —
Alfred and estate-manager — are outside this checkout.  So
:class:`TestTheNoConsumerReasonsHoldForTheTray` computes **one limb of a
conjunction** and says so in its name: it can refute *no consumer* and can
never confirm it.  ``ports_checked``' rule, at the size of a reason cell.
"""

from __future__ import annotations

import re

import pytest

from sysadmin.core.config import REPO_ROOT
from tests.document_claims import (
    contract_class_names,
    live_route_contracts,
    normalise_path,
    tray_consumption,
)

CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

#: The heading the registry lives under, and the heading that ends it.  The
#: region is bounded rather than the whole file being scanned, because
#: ``CLAUDE.md`` carries three other Markdown tables — the documentation map,
#: the database settings — whose rows are not endpoints.
_SECTION_START = "## Contract Registry"
_SECTION_END = "## Detailed Documentation"

#: The exemption table's own heading sentence.  Matched on the bold lead-in
#: rather than on the table, because a table is recognisable only by what
#: precedes it and two tables in one section are otherwise indistinguishable.
_EXEMPTION_LEAD = "**Served with no contract model**"

#: The consumed table's lead-in.  Its rows name another service's routes and
#: must not be swept against this application's.
_CONSUMED_LEAD = "**Consumed from estate-manager on 8400**"


def _registry_section() -> str:
    text = CLAUDE_MD.read_text()
    start = text.index(_SECTION_START)
    end = text.index(_SECTION_END, start)
    return text[start:end]


def _table_rows(region: str) -> list[tuple[str, str, str]]:
    """Every three-celled Markdown row in ``region`` whose first cell is code.

    The leading backtick is the discriminator: a header row and its
    ``|---|`` separator both fail it, and so would a prose table added later.
    """
    rows: list[tuple[str, str, str]] = []
    for line in region.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 3:
            rows.append((cells[0], cells[1], cells[2]))
    return rows


def _endpoint_pairs(cell: str) -> set[tuple[str, str]]:
    """Parse an endpoint cell into ``(method, path)`` pairs.

    Serves every spelling the document uses at once: ``` `GET /health` ```,
    and ``` `GET`/`POST /api/sysadmin/dnd` ``` — one path registered by two
    decorators, which the document writes as one row because it is one shape.
    A cell naming no method or no path yields nothing rather than raising, so
    the totality tests report it as an unaccounted-for route rather than as a
    collection error; an error would name the wrong fault.
    """
    tokens = " ".join(re.findall(r"`([^`]+)`", cell)).split()
    methods = [token for token in tokens if token.isupper()]
    paths = [token for token in tokens if token.startswith(("/", ":"))]
    return {
        (method, normalise_path(path))
        for method in methods
        for path in paths
    }


def _split_tables() -> tuple[
    list[tuple[str, str, str]], list[tuple[str, str, str]], list[tuple[str, str, str]]
]:
    """The registry, consumed and exemption tables, in that order."""
    region = _registry_section()
    consumed_at = region.index(_CONSUMED_LEAD)
    exempt_at = region.index(_EXEMPTION_LEAD)
    assert consumed_at < exempt_at, "the consumed table is expected first"
    return (
        _table_rows(region[:consumed_at]),
        _table_rows(region[consumed_at:exempt_at]),
        _table_rows(region[exempt_at:]),
    )


def registry_pairs() -> set[tuple[str, str]]:
    served, _, _ = _split_tables()
    return {pair for row in served for pair in _endpoint_pairs(row[0])}


def exempt_pairs() -> set[tuple[str, str]]:
    _, _, exempt = _split_tables()
    return {pair for row in exempt for pair in _endpoint_pairs(row[0])}


def consumed_pairs() -> set[tuple[str, str]]:
    _, consumed, _ = _split_tables()
    return {pair for row in consumed for pair in _endpoint_pairs(row[0])}


# --------------------------------------------------------------------------


class TestTheInstrumentDoesNotCollapse:
    """Rule 3: a normalisation that merges two routes measures neither."""

    def test_normalisation_is_injective_over_the_live_routes(self):
        from sysadmin.main import create_app
        from tests.document_claims import FASTAPI_OWN_PATHS

        raw = {
            (method, route.path)
            for route in create_app().routes
            if route.path not in FASTAPI_OWN_PATHS
            for method in getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
        }
        collapsed = {(method, normalise_path(path)) for method, path in raw}
        assert len(collapsed) == len(raw), (
            "normalise_path merged two distinct routes; the sweep below would "
            "compare fewer things than it believes"
        )

    def test_it_normalises_the_spellings_the_document_actually_differs_on(self):
        assert normalise_path("/api/sysadmin/alerts/{id}/ack") == normalise_path(
            "/api/sysadmin/alerts/{alert_id}/ack"
        )
        assert normalise_path("/api/sysadmin/services/{name}/details") == normalise_path(
            "/api/sysadmin/services/{service_name}/details"
        )

    def test_it_does_not_normalise_away_a_real_difference(self):
        assert normalise_path("/api/logs/recent") != normalise_path("/api/logs/{source}")


class TestTheTablesParse:
    """The extraction is the premise of every sweep below it."""

    def test_the_three_tables_are_found_and_none_is_empty(self):
        served, consumed, exempt = _split_tables()
        assert served, "no rows parsed from the served registry table"
        assert consumed, "no rows parsed from the consumed table"
        assert exempt, "no rows parsed from the exemption table"

    def test_the_two_method_row_yields_two_pairs(self):
        pairs = _endpoint_pairs("`GET`/`POST /api/sysadmin/dnd`")
        assert pairs == {
            ("GET", "/api/sysadmin/dnd"),
            ("POST", "/api/sysadmin/dnd"),
        }

    def test_a_cell_naming_no_path_yields_nothing_rather_than_raising(self):
        assert _endpoint_pairs("`HealthResponse`") == set()

    def test_the_documentation_map_table_is_outside_the_region(self):
        assert "Read This File" not in _registry_section()


class TestEveryServedRouteIsAccountedFor:
    """Rule 2: the document supplies the partition; this checks totality."""

    def test_no_live_route_is_missing_from_both_tables(self):
        live = set(live_route_contracts())
        unaccounted = sorted(live - registry_pairs() - exempt_pairs())
        assert not unaccounted, (
            "served but named in neither CLAUDE.md table: "
            + ", ".join(f"{method} {path}" for method, path in unaccounted)
        )

    def test_no_route_is_in_both_tables(self):
        both = sorted(registry_pairs() & exempt_pairs())
        assert not both, (
            "named as both contracted and uncontracted: "
            + ", ".join(f"{method} {path}" for method, path in both)
        )

    def test_every_registry_row_names_a_live_route(self):
        live = set(live_route_contracts())
        stale = sorted(registry_pairs() - live)
        assert not stale, (
            "registry rows for routes this service does not serve — "
            "SNAG-DOCS-001's shape: "
            + ", ".join(f"{method} {path}" for method, path in stale)
        )

    def test_every_exemption_row_names_a_live_route(self):
        live = set(live_route_contracts())
        stale = sorted(exempt_pairs() - live)
        assert not stale, (
            "exemption rows for routes this service does not serve: "
            + ", ".join(f"{method} {path}" for method, path in stale)
        )

    def test_the_consumed_rows_are_not_served_here(self):
        live = {path for _, path in live_route_contracts()}
        for _, path in consumed_pairs():
            assert path.startswith(":8400"), (
                f"a consumed row must name the producer's port: {path}"
            )
            assert path.removeprefix(":8400") not in live, (
                f"{path} is listed as consumed and is served here as well"
            )


class TestAContractCannotBeExempted:
    """Rule 1: the exemption list can only excuse what the code left unpinned."""

    def test_no_pinned_route_appears_in_the_exemption_table(self):
        pinned = {pair for pair, model in live_route_contracts().items() if model}
        hidden = sorted(pinned & exempt_pairs())
        assert not hidden, (
            "these routes declare a contracts.py response_model and are "
            "excused from the registry anyway: "
            + ", ".join(f"{method} {path}" for method, path in hidden)
        )

    def test_every_pinned_route_has_a_registry_row(self):
        pinned = {pair for pair, model in live_route_contracts().items() if model}
        missing = sorted(pinned - registry_pairs())
        assert not missing, (
            "pinned to a contracts.py model with no registry row: "
            + ", ".join(f"{method} {path}" for method, path in missing)
        )

    def test_the_pinned_population_is_not_empty(self):
        """An anti-vacuity premise: the two tests above pass over an empty set."""
        pinned = {pair for pair, model in live_route_contracts().items() if model}
        assert len(pinned) > 20, f"only {len(pinned)} routes pinned; expected ~30"


class TestEveryRowsEnforcementIsTrue:
    """Rule 4: measured correct 36 of 36 before this existed — a regression
    guard, not a repair."""

    def _served_rows(self):
        served, _, _ = _split_tables()
        bound = live_route_contracts()
        for endpoint, model, enforcement in served:
            for pair in _endpoint_pairs(endpoint):
                if pair in bound:
                    yield pair, model, enforcement, bound[pair]

    def test_a_response_model_claim_means_the_route_declares_one(self):
        wrong = [
            pair
            for pair, _model, enforcement, live in self._served_rows()
            if enforcement.startswith("response_model") and live is None
        ]
        assert not wrong, f"claim a response_model and declare none: {wrong}"

    def test_a_parse_side_claim_means_the_route_declares_none(self):
        wrong = [
            pair
            for pair, _model, enforcement, live in self._served_rows()
            if not enforcement.startswith("response_model") and live is not None
        ]
        assert not wrong, f"claim parse-side only and declare a response_model: {wrong}"

    def test_the_first_model_named_is_the_one_the_route_declares(self):
        wrong = []
        for pair, model, enforcement, live in self._served_rows():
            if not enforcement.startswith("response_model"):
                continue
            named = re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", model)
            if not named or named[0] != live:
                wrong.append((pair, named[:1], live))
        assert not wrong, f"registry names the wrong model: {wrong}"


class TestTheExemptionRowsCarryAReason:
    """Rule 2 again: a bare list is the count that names nothing."""

    def test_every_exemption_row_states_why_it_has_no_contract(self):
        _, _, exempt = _split_tables()
        for endpoint, returns, reason in exempt:
            assert len(reason) >= 20, f"{endpoint}: reason too thin to be one"
            assert returns, f"{endpoint}: does not say what it returns"

    def test_the_tombstones_are_named_by_their_status_and_not_by_prose(self):
        """Keyed on the ``Returns`` cell, never on the word "tombstone".

        The first draft matched the word and went red on
        ``GET /api/logs/{source}``, whose reason *mentions* the tombstones
        because it is the catch-all they are declared above.  A guard keyed
        on wording pins prose; ``410 Gone`` is the structural fact, and it is
        also the one exemption reason that is not a judgement.
        """
        _, _, exempt = _split_tables()
        gone = {
            endpoint for endpoint, returns, _reason in exempt if "410" in returns
        }
        assert len(gone) == 2, f"expected the two removed paths, found {sorted(gone)}"
        for endpoint, _returns, _reason in exempt:
            if endpoint in gone:
                assert "summary" in endpoint


class TestTheDocumentStillNamesItsOwnGuard:
    """A rule stated in prose and enforced nowhere is what this entry was."""

    def test_the_section_names_this_module(self):
        assert "tests/test_claude_md_registry.py" in _registry_section()

    def test_the_membership_sentence_is_narrowed_to_the_models(self):
        """Bound to the sentence's own clause, never to a character window.

        The first draft read the 200 characters after the claim and looked
        for ``models``.  Driven at the mutation that deletes the narrowing it
        stayed **green**, because the paragraph continues *"It carried eight
        project response models…"* — the guard matched a different sentence's
        prose.  An append-only narrative makes a substring test monotonic:
        the longer the section grows, the more certainly any word appears
        somewhere after any other.  The window is the qualifying sentence
        itself now, and the emphasis is what is asserted, because the plain
        word occurs throughout this document and the **correction** does not.
        """
        region = _registry_section()
        sentence = "membership is a property a test computes"
        assert sentence in region
        rest = region[region.index(sentence) + len(sentence) :]
        clause = rest[: rest.index(".") + 1]
        assert "**models**" in clause, (
            "the SNAG-DOCS-002 sentence must say in its own clause which half "
            "it is about, or it reads as a guarantee about the routes that no "
            f"test provided; clause was {clause!r}"
        )


@pytest.mark.parametrize(
    "path",
    ["/api/logs/review", "/api/logs/review/generate"],
)
def test_the_two_routes_the_sweep_found_are_listed(path):
    """The live defect this guard was written by finding.

    Named individually rather than left to the totality test, because a
    regression here would otherwise be one line in a list of fourteen.
    """
    pairs = {pair[1] for pair in registry_pairs()}
    assert path in pairs


# --------------------------------------------------------------------------
# SNAG-DOCS-017 — the consumer half


def _rows_with_enforcement() -> list[tuple[tuple[str, str], str, str]]:
    """``(pair, model cell, enforcement cell)`` for the served and consumed
    tables together.

    The two tables are swept as one population because a consumed row makes
    the *same* claim: nothing here declares a ``response_model`` for a route
    another service serves, so every one of them is a parse-side assertion by
    construction.
    """
    served, consumed, _ = _split_tables()
    out = []
    for endpoint, model, enforcement in served + consumed:
        for pair in _endpoint_pairs(endpoint):
            out.append((pair, model, enforcement))
    return out


def _first_model_named(cell: str) -> str | None:
    named = re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", cell)
    return named[0] if named else None


def _is_producer_claim(enforcement: str) -> bool:
    return enforcement.startswith("response_model")


def _is_serialise_side(enforcement: str) -> bool:
    return "serialise-side" in enforcement


class TestTheWalkMeasuresWhatItClaims:
    """Premises.  Every sweep below is worthless if these are wrong, and two
    of them are the specimens that forced the walk's two hardest rules."""

    def test_the_liveness_probe_is_not_paired_with_the_status_model(self):
        """Rule 1's specimen, and the reason the anchor is not the function.

        ``fetch_status`` issues ``GET /health`` for liveness and then ``GET
        /api/sysadmin/status``, and parses once.  A function-level pairing —
        the obvious implementation — reports that the tray parses ``/health``
        with ``StatusResponse``, which would then satisfy a registry row that
        claimed it.  It is the only method in this tray that requests twice,
        so this is the whole observable population of the rule.
        """
        consumption = tray_consumption()
        assert ("GET", "/health") in consumption.requests, (
            "the liveness probe is no longer issued; this premise is stale"
        )
        assert ("GET", "/health") not in consumption.parses, (
            "the walk paired the liveness probe with a model — the anchor has "
            "widened from the nearest preceding request to the function"
        )
        assert consumption.parses[("GET", "/api/sysadmin/status")] == frozenset(
            {"StatusResponse"}
        )

    def test_the_estate_routes_keep_the_producers_port(self):
        """Rule 2.  Without the prefix the walk reports this service as
        serving the estate's two project routes — ``SNAG-DOCS-001``'s shape
        arriving from the consumer side."""
        parses = tray_consumption().parses
        assert ("GET", ":8400/api/projects/overview") in parses
        assert ("GET", "/api/projects/overview") not in parses

    def test_exactly_one_indirect_helper_is_found(self):
        """Rule 3: the population is reported, never assumed.

        **This is the only test that announces a new helper**, which is why
        it pins equality rather than membership.  A second helper is caught
        by the sweeps below only if it happens to parse a route the document
        mishandles; one parsing a correctly-listed route is invisible
        everywhere else, and correctly so.  A red here is therefore a prompt
        to confirm the new helper's call sites resolve — not, by itself, a
        defect in the document.

        Zero is the reading that refuses: the helper shape carries five of
        this tray's sixteen parses, so a walk that found no helper has gone
        quiet about a third of the population while still looking plausible.
        """
        found = tray_consumption().indirect_helpers
        assert found, (
            "no indirect fetch helper found; five parses are silently missing "
            "and every sweep below is measuring a smaller tray than exists"
        )
        assert found == frozenset({"_fetch_file_endpoint"}), (
            f"the helper population has moved to {sorted(found)} — confirm each "
            "one's call sites resolve to a (path, model) pair before repinning"
        )

    def test_both_call_shapes_reach_the_result(self):
        """The direct shape and the helper shape, each with a witness.

        Driven because the helper's path is a *parameter*: the predicate that
        reads a direct call refuses it correctly, so a walk with one
        predicate drops five of sixteen parses and reports a smaller,
        entirely plausible answer.
        """
        parses = tray_consumption().parses
        assert parses.get(("GET", "/api/sysadmin/alerts")) == frozenset(
            {"AlertsResponse"}
        ), "the direct shape is missing"
        assert parses.get(("GET", "/api/files/duplicates")) == frozenset(
            {"DuplicatesResponse"}
        ), "the _fetch_file_endpoint shape is missing"

    def test_the_parsed_population_is_not_empty(self):
        """An anti-vacuity premise: every sweep below passes over an empty
        walk, and a walk that found nothing is exactly what a broken
        predicate produces."""
        parses = tray_consumption().parses
        assert len(parses) > 10, f"only {len(parses)} parses found; expected ~16"

    def test_every_model_the_tray_parses_with_is_a_contract(self):
        """Empty finding population, and stated rather than assumed.

        The walk keeps **raw** names so that "parsed by something that is not
        a contract" and "not parsed at all" do not spell the same way.
        Nothing on this box is in the first class today; a name appearing
        here is not necessarily a defect, but it is a route whose registry
        row would be claiming more than the tray does.
        """
        contracts = contract_class_names()
        strangers = sorted(
            (pair, sorted(set(names) - contracts))
            for pair, names in tray_consumption().parses.items()
            if set(names) - contracts
        )
        assert not strangers, f"parsed with non-contract models: {strangers}"


class TestEveryParseSideRowIsTrue:
    """The claim nine rows made in prose and nothing computed.

    ``tests/test_contracts.py`` guards the round trip — that these models can
    parse what the routes emit — which is a different question from whether
    the tray *does*.  A row could name a model nobody hands a payload to and
    both guards would stay green.
    """

    def test_a_parse_side_row_names_a_model_the_tray_actually_parses_with(self):
        consumption = tray_consumption()
        wrong = []
        for pair, model_cell, enforcement in _rows_with_enforcement():
            if _is_producer_claim(enforcement) or _is_serialise_side(enforcement):
                continue
            named = _first_model_named(model_cell)
            actual = consumption.parses.get(pair, frozenset())
            if named not in actual:
                wrong.append((pair, named, sorted(actual)))
        assert not wrong, (
            "rows claiming the tray parses them, where it does not — "
            f"(route, claimed, actually parsed with): {wrong}"
        )

    def test_the_serialise_side_row_is_honest_about_not_being_parsed(self):
        """``GET /api/sysadmin/events`` is the ninth row and the one the
        producer-half sweep could not distinguish.

        Its cell says **serialise**-side: the model shapes each SSE ``data:``
        line on the way out, and no consumer in this checkout parses it back.
        That is a different claim from the other eight and is checked as one,
        because admitting it to the sweep above would demand a tray parse the
        document never asserted.
        """
        consumption = tray_consumption()
        serialise = [
            pair
            for pair, _model, enforcement in _rows_with_enforcement()
            if _is_serialise_side(enforcement)
        ]
        assert serialise == [("GET", "/api/sysadmin/events")], (
            f"the serialise-side population has moved: {serialise}"
        )
        assert ("GET", "/api/sysadmin/events") not in consumption.parses, (
            "the tray parses the event stream now, so the row's enforcement "
            "cell should say parse-side rather than serialise-side"
        )


class TestTheExemptionTableCannotHideAConsumerContract:
    """Rule 7 — rule 1's clause, owed on the side it could not reach."""

    def test_no_route_the_tray_parses_is_excused_from_the_registry(self):
        parsed = {
            pair
            for pair, names in tray_consumption().parses.items()
            if set(names) & contract_class_names()
        }
        hidden = sorted(parsed & exempt_pairs())
        assert not hidden, (
            "the tray parses these with a contracts.py model and the document "
            "excuses them from the registry anyway: "
            + ", ".join(f"{method} {path}" for method, path in hidden)
        )

    def test_every_route_the_tray_parses_has_a_row(self):
        """The membership *iff*, read from the consumer end.

        A route pinned only by the tray's parse still belongs in the
        registry, and before the walk nothing could say so.
        """
        parsed = {
            pair
            for pair, names in tray_consumption().parses.items()
            if set(names) & contract_class_names()
        }
        missing = sorted(parsed - registry_pairs() - consumed_pairs())
        assert not missing, (
            "parsed by the tray with a contracts.py model and in neither the "
            "served nor the consumed table: "
            + ", ".join(f"{method} {path}" for method, path in missing)
        )


class TestTheNoConsumerReasonsHoldForTheTray:
    """**One limb of a conjunction, and the name says so.**

    Four exemption reasons say *no consumer*.  Two of this repository's
    consumers — Alfred, which pulls the briefing, and estate-manager, which
    pulls ``by-project`` once per scan — are outside this checkout, so no
    test here can confirm that claim.  It can refute it: a route the tray
    requests is one that has a consumer, whatever else is true.
    ``ports_checked``' rule at the size of a reason cell — the narrower
    finding is reported as the narrower finding.
    """

    def _reasons(self) -> list[tuple[tuple[str, str], str]]:
        _, _, exempt = _split_tables()
        return [
            (pair, reason)
            for endpoint, _returns, reason in exempt
            for pair in _endpoint_pairs(endpoint)
        ]

    def test_a_row_claiming_no_consumer_is_not_requested_by_the_tray(self):
        requests = tray_consumption().requests
        wrong = [
            pair
            for pair, reason in self._reasons()
            if "no consumer" in reason.lower() and pair in requests
        ]
        assert not wrong, (
            "the reason says no consumer and the tray requests it: "
            + ", ".join(f"{method} {path}" for method, path in wrong)
        )

    def test_the_no_consumer_population_is_the_four_that_were_measured(self):
        """An anti-vacuity premise: the test above passes over an empty set,
        and the reasons are prose that a rewording could silently empty."""
        claimed = sorted(
            pair for pair, reason in self._reasons() if "no consumer" in reason.lower()
        )
        assert len(claimed) == 4, f"expected four such reasons, found {claimed}"

    def test_the_scan_row_claims_a_request_without_a_parse_and_both_halves_hold(self):
        """``POST /api/files/scan`` is the one exemption reason the walk can
        confirm in *both* directions.

        Its reason says the tray consumes it and *"reads the status code and
        never the body"* — so the route must be in the requests and absent
        from the parses.  A reason that is checkable on both halves is worth
        naming individually, because it is the only one that discriminates a
        walk which found nothing from one that worked.
        """
        consumption = tray_consumption()
        pair = ("POST", "/api/files/scan")
        assert pair in consumption.requests, (
            "the reason claims the tray calls this and the walk did not see it"
        )
        assert pair not in consumption.parses, (
            "the reason claims the body is never parsed, and it is"
        )
