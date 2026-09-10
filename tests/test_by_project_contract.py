"""GET /api/services/by-project — the one surface this repository publishes.

``SNAG-DOCS-018``, 2026-09-10.  Every other contract in
``sysadmin/core/contracts.py`` describes a payload the **tray** parses, in
this checkout, against a producer in this checkout.  This one describes a
payload ``estate-manager`` pulls once per scan over :8400's scanner
(their ADR-0008, this repository's ADR-0005), so nothing local reads it and
the route had no test of any kind until this file.

**The tests assert the wrapper, never the mapping**, and that is the whole
point of the entry.  The consumer reads
``payload.get("by_project", payload)`` — two limbs, the second accepting a
bare mapping — so a model over ``dict[str, list[str]]`` would have been the
smaller-looking pin and would have changed the wire.  Pinning the wrapper
makes their second limb *unreachable* rather than merely unexercised, and
that is a property of this payload that a test here can hold and a test
there cannot.

Their parse is deliberately **not** imported or reproduced.  Modelling a
consumer's tolerance in the producer's suite is what the Contract Registry
refuses in writing — collapsing a producer's guarantee into the consumer's
defensiveness — so what is asserted here is the shape their first limb
needs, with the reason named rather than the code borrowed.
"""

import pytest

from sysadmin.core.contracts import ServicesByProjectResponse
from tests.conftest import set_services

ROUTE = "/api/services/by-project"


def _two_projects():
    set_services(
        {
            "name": "alfred-backend",
            "kind": "http",
            "url": "http://127.0.0.1:8110",
            "project": "alfred",
        },
        {
            "name": "alfred-frontend",
            "kind": "http",
            "url": "http://127.0.0.1:3110",
            "project": "alfred",
        },
        {
            "name": "sysadmin",
            "kind": "http",
            "url": "http://127.0.0.1:8500",
            "project": "sysadmin_assistant",
        },
        # No project: contributes nothing, and that is the producer's rule.
        {"name": "postgres", "kind": "tcp", "host": "127.0.0.1", "port": 5432},
    )


@pytest.mark.asyncio
class TestTheWrapperIsTheContract:
    """Rule 1 of the model: the top-level key is what is pinned."""

    async def test_the_payload_is_wrapped_in_by_project(self, test_client):
        _two_projects()
        payload = (await test_client.get(ROUTE)).json()
        assert "by_project" in payload, (
            "the estate reads payload.get('by_project', payload); serving the "
            "bare mapping falls through to its second limb and changes the wire"
        )

    async def test_the_wrapper_is_the_only_top_level_key(self, test_client):
        """A second key is a wire change, so it is an announcement.

        Every sibling response model in ``contracts.py`` carries a ``count``
        beside its collection.  This one refuses on measurement rather than
        on taste — ``get_services()`` raises on a ``services.yaml`` it cannot
        read, so the mapping is never empty-because-blind and there is no
        ambiguity for a count to resolve.
        """
        _two_projects()
        payload = (await test_client.get(ROUTE)).json()
        assert set(payload) == {"by_project"}

    async def test_the_mapping_is_project_id_to_a_list_of_names(self, test_client):
        _two_projects()
        by_project = (await test_client.get(ROUTE)).json()["by_project"]
        assert by_project == {
            "alfred": ["alfred-backend", "alfred-frontend"],
            "sysadmin_assistant": ["sysadmin"],
        }
        assert all(isinstance(k, str) for k in by_project)
        assert all(isinstance(n, str) for names in by_project.values() for n in names)

    async def test_a_service_declaring_no_project_contributes_nothing(
        self, test_client
    ):
        """Stated because the consumer cannot tell an absent project from a
        dropped one — it coerces whatever arrives."""
        _two_projects()
        by_project = (await test_client.get(ROUTE)).json()["by_project"]
        assert "postgres" not in {n for names in by_project.values() for n in names}

    async def test_no_services_is_an_empty_mapping_and_not_an_absent_key(
        self, test_client
    ):
        set_services()
        payload = (await test_client.get(ROUTE)).json()
        assert payload == {"by_project": {}}


class TestThePinIsAContractAndNotADict:
    """Provenance, not value.

    ``-> dict`` makes FastAPI infer a ``response_model`` of ``dict``, so the
    route *declared* one for its whole life and pinned nothing — which is
    why asserting that some model is bound would have passed against the
    defect.  What is asserted is **which** class, and that it is the one
    ``CLAUDE.md``'s registry names.
    """

    def test_the_route_declares_the_contracts_model(self, test_app):
        bound = [
            getattr(r, "response_model", None)
            for r in test_app.routes
            if getattr(r, "path", None) == ROUTE
        ]
        assert bound == [ServicesByProjectResponse], (
            f"by-project is pinned to {bound}, not the contracts.py model"
        )

    def test_the_model_declares_the_wrapper_and_nothing_else(self):
        assert set(ServicesByProjectResponse.model_fields) == {"by_project"}

    def test_an_absent_wrapper_parses_to_an_empty_mapping(self):
        """``Contract``'s defensiveness, inherited and stated.

        No local code calls ``from_dict`` on this model — the consumer is
        another repository — so the tolerance is asserted here or nowhere.
        """
        assert ServicesByProjectResponse.from_dict({}).by_project == {}
