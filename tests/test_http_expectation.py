"""The ``expect:`` body condition on ``kind: http`` entries.

Estate message ``ed301e95``: venture-assistant's dedupe stalled for 44
hours while ``GET /pipeline/status`` answered 200 with ``stalled: true``,
because the check judged the status code alone.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import yaml
from pydantic import ValidationError

from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.services import (
    HttpExpectation,
    ServiceEntry,
    evaluate_expectation,
    parse_services,
)

SERVICES_YAML = Path(__file__).resolve().parents[1] / "services.yaml"


def _expect(path: str = "stalled", equals=False) -> HttpExpectation:
    return HttpExpectation(path=path, equals=equals)


class TestEvaluateExpectation:
    def test_the_declared_value_is_met(self):
        assert evaluate_expectation(_expect(), {"stalled": False})[0] == "met"

    def test_a_different_value_is_unmet_and_names_what_it_found(self):
        verdict, evidence = evaluate_expectation(_expect(), {"stalled": True})
        assert verdict == "unmet"
        assert evidence["actual"] is True

    def test_a_nested_path_descends_through_objects(self):
        body = {"search": {"ok": True, "fresh": True}}
        assert evaluate_expectation(_expect("search.ok", True), body)[0] == "met"
        assert (
            evaluate_expectation(_expect("search.ok", True), {"search": {"ok": False}})[0]
            == "unmet"
        )

    def test_an_absent_field_is_unevaluable_never_met(self):
        # A renamed field must not retire the check in silence.
        verdict, evidence = evaluate_expectation(_expect(), {"is_stalled": True})
        assert verdict == "unevaluable"
        assert "'stalled'" in evidence["error"]

    def test_descending_into_a_scalar_is_unevaluable(self):
        verdict, _ = evaluate_expectation(_expect("search.ok", True), {"search": "up"})
        assert verdict == "unevaluable"

    def test_a_body_that_is_not_an_object_is_unevaluable(self):
        assert evaluate_expectation(_expect(), [False])[0] == "unevaluable"

    def test_zero_does_not_satisfy_false(self):
        # Python's `0 == False` is True; JSON's is not.
        assert evaluate_expectation(_expect(), {"stalled": 0})[0] == "unmet"

    def test_true_does_not_satisfy_one(self):
        assert evaluate_expectation(_expect("n", 1), {"n": True})[0] == "unmet"

    def test_numbers_compare_across_int_and_float(self):
        assert evaluate_expectation(_expect("n", 1), {"n": 1.0})[0] == "met"

    def test_null_is_a_value_that_can_be_expected(self):
        assert evaluate_expectation(_expect("err", None), {"err": None})[0] == "met"
        assert evaluate_expectation(_expect("err", None), {})[0] == "unevaluable"


class TestTheDeclaration:
    def test_yaml_false_stays_a_bool(self):
        entry = parse_services(
            yaml.safe_load(
                "schema: 1\nservices:\n"
                "  - name: p\n    kind: http\n    url: http://x/s\n"
                "    expect: { path: stalled, equals: false }\n"
            )
        ).services[0]
        assert entry.expect is not None
        assert entry.expect.equals is False

    def test_it_is_refused_on_a_kind_that_never_reads_it(self):
        with pytest.raises(ValidationError, match="expect"):
            ServiceEntry(
                name="t", kind="systemd",
                systemd={"unit": "t.service"},
                expect={"path": "a", "equals": True},
            )

    def test_an_unknown_key_in_it_is_refused(self):
        with pytest.raises(ValidationError):
            ServiceEntry(
                name="t", kind="http", url="http://x",
                expect={"path": "a", "equal": True},
            )

    def test_an_empty_path_is_refused(self):
        with pytest.raises(ValidationError):
            HttpExpectation(path="", equals=True)


@pytest.fixture
def agent():
    a = SysAdminAgent()
    a._http.attach(AsyncMock(spec=httpx.AsyncClient))
    return a


def _response(status: int, body) -> MagicMock:
    resp = MagicMock(status_code=status)
    if isinstance(body, str):
        resp.json = MagicMock(side_effect=json.JSONDecodeError("bad", body, 0))
    else:
        resp.json = MagicMock(return_value=body)
    return resp


@pytest.fixture
def pipeline():
    return ServiceEntry(
        name="pipeline", kind="http", url="http://localhost:8300/pipeline/status",
        expect={"path": "stalled", "equals": False},
    )


class TestTheCheckReadsTheBody:
    @pytest.mark.asyncio
    async def test_a_200_carrying_the_fault_is_degraded(self, agent, pipeline):
        agent._http.client.get = AsyncMock(
            return_value=_response(200, {"stalled": True, "unlinked": 4653})
        )
        status, ms, details = await agent._check_http(pipeline)
        assert status == "degraded"
        assert isinstance(ms, int)
        assert details["expect"]["verdict"] == "unmet"
        assert details["reason"] == "stalled is true, expected false"

    @pytest.mark.asyncio
    async def test_a_200_meeting_the_condition_is_ok(self, agent, pipeline):
        agent._http.client.get = AsyncMock(
            return_value=_response(200, {"stalled": False})
        )
        status, _, details = await agent._check_http(pipeline)
        assert (status, details) == ("ok", {})

    @pytest.mark.asyncio
    async def test_a_body_that_is_not_json_is_degraded_not_ok(self, agent, pipeline):
        agent._http.client.get = AsyncMock(return_value=_response(200, "<html>"))
        status, _, details = await agent._check_http(pipeline)
        assert status == "degraded"
        assert details["expect"]["verdict"] == "unevaluable"
        assert "not JSON" in details["reason"]

    @pytest.mark.asyncio
    async def test_a_renamed_field_is_degraded_not_ok(self, agent, pipeline):
        agent._http.client.get = AsyncMock(
            return_value=_response(200, {"is_stalled": False})
        )
        status, _, details = await agent._check_http(pipeline)
        assert status == "degraded"
        assert details["expect"]["verdict"] == "unevaluable"

    @pytest.mark.asyncio
    async def test_the_status_code_still_decides_first(self, agent, pipeline):
        resp = _response(503, {"stalled": False})
        agent._http.client.get = AsyncMock(return_value=resp)
        status, _, _ = await agent._check_http(pipeline)
        assert status == "critical"
        resp.json.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_entry_without_expect_never_reads_the_body(self, agent):
        resp = _response(200, {"stalled": True})
        agent._http.client.get = AsyncMock(return_value=resp)
        plain = ServiceEntry(name="w", kind="http", url="http://x/health")
        assert (await agent._check_http(plain))[0] == "ok"
        resp.json.assert_not_called()


class TestTheShippedDeclaration:
    """The entry the message asked for, as ``services.yaml`` ships it."""

    def _entry(self) -> ServiceEntry:
        raw = yaml.safe_load(SERVICES_YAML.read_text())
        entries = parse_services(raw).services
        return next(e for e in entries if e.name == "venture-pipeline")

    def test_it_polls_the_status_route_for_stalled_false(self):
        entry = self._entry()
        assert entry.url == "http://localhost:8300/pipeline/status"
        assert entry.expect == HttpExpectation(path="stalled", equals=False)

    def test_it_claims_no_port(self):
        # 8300 is venture-assistant's backend entry's claim; a second
        # claim on it is a `duplicate_claim` about one process, and the
        # estate's health audit reads only port-carrying entries, where
        # /pipeline/status — a status report — does not belong.
        assert self._entry().port is None
