"""The GPU gate is the single read, and both halves of that decision are pinned.

``estate.gpu.sustained_busy`` licenses a blocking ~1.5 s min-of-N window
**wherever nobody is waiting on the answer**, and refuses it where a
request is held open (estate ADR-0074 §2, announced here as message
``df4113cb``).  The test is about the *invocation*, not the function, and
the library states its own tie-breaker: a caller that cannot answer the
question for every one of its invocations keeps the single read.

:func:`sysadmin.core.llm_client.LLMClient.generate` cannot.  One gate is
reached by three ``run_weekly_review`` jobs with nobody waiting and by
three ``POST …/review/generate`` routes that ``await`` the same function
inline — estate-manager's own ``SNAG-ESTATE-090`` shape at three gates
rather than one.  Session 134 costed the split and refused it: the
window rescues a ~1-in-120 transient on a path that fires three times a
week, and a false defer costs prose rather than a review.

**The waiterless half took a lease on 2026-08-31 and that makes the
refusal stronger, not weaker** (``SNAG-SCHED-003``).  The three Monday
jobs now hold an estate GPU lease and pass ``gpu_lease_held=True``, so
they skip the gate entirely — the arbiter has already read the card on
their behalf, as a *retry* rather than a refusal, and it holds the card
until release.  What is left in the gate's population is the three
``POST …/review/generate`` routes alone, which is precisely the class the
single read is right for.  So ``sustained_busy``'s population here is now
**empty**, and the window is refused for a second, independent reason.

That is why the first guard below is kept and reworded rather than
deleted: it no longer asks whether the waiterless class reaches the
*gate*, it asks whether it reaches the *review*, and a third guard asks
whether it takes a lease on the way.  Deleting a control because its
subject moved is how a repository stops noticing that the subject moved
back.

Three guards, because the decision has three ways to go stale:

* **The premise.**  If the routes ever stop holding the request open —
  dispatched to a task, answered 202 — every invocation becomes
  waiterless and the refusal is re-openable.  Nothing else would say so.
* **The lease.**  If a weekly job stops taking one, the waiterless class
  is back in the gate's population and back to reading the card once
  inside another repository's five-and-three-quarter-hour hold, which is
  ``SNAG-SCHED-003``'s whole symptom.  Nothing else would say so: the job
  still calls ``generate_review``, still stores a review, and still logs
  ``weekly_*_review_generated`` — it just quietly serves a digest.
* **The rule, pre-staged.**  Its population is empty today and it starts
  asserting the day somebody adopts the window: every call site here
  runs inside an event loop, so an unthreaded ``sustained_busy`` stalls
  every other request for the whole window.  The detector is driven at
  synthetic sources in both directions, because a sweep that finds
  nothing over a population of zero is not evidence of anything.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

#: Each gate, by the module holding its ``generate_review`` and the
#: router holding the request-held-open caller of the same function.  A
#: fourth review adds a line here; one absent from this tuple is a gate
#: nothing checks.
REVIEW_GATES = (
    ("sysadmin.files.review", "sysadmin.files.router"),
    ("sysadmin.monitor.log_review", "sysadmin.monitor.routers.logs"),
    ("sysadmin.monitor.health_review", "sysadmin.monitor.routers.sysadmin"),
)

GATED_CALL = "generate_review"
JOB_ENTRY_POINT = "run_weekly_review"
LEASE_ACQUIRE = "acquire_review_lease"
LEASE_RELEASE = "release_review_lease"
HELD_FLAG = "gpu_lease_held"
WINDOW = "sustained_busy"
SINGLE_READ = "ensure_gpu_idle"

#: The package swept for an adopted window.
PACKAGE_ROOT = Path(__file__).resolve().parent.parent / "sysadmin"


def _tree(module_path: str) -> ast.Module:
    module = __import__(module_path, fromlist=["_"])
    return ast.parse(Path(inspect.getfile(module)).read_text())


def _function(tree: ast.Module, name: str) -> ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"no async def {name}")


def _alias_for(tree: ast.Module, module_path: str) -> str:
    """The name a router binds ``module_path`` to.

    Resolved from the router's own imports rather than transcribed, so a
    rename cannot leave this suite asserting against a name nobody uses.
    """
    package, _, leaf = module_path.rpartition(".")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == package:
            for alias in node.names:
                if alias.name == leaf:
                    return alias.asname or alias.name
    raise AssertionError(f"nothing imports {leaf} from {package}")


def _is_post_route(node: ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(d, ast.Call)
        and isinstance(d.func, ast.Attribute)
        and d.func.attr == "post"
        for d in node.decorator_list
    )


def _awaits_attribute_call(node: ast.AST, owner: str, attr: str) -> bool:
    """Is ``await owner.attr(...)`` present, awaited rather than dispatched?

    The awaited-ness is the whole point: a handler that handed this to
    ``asyncio.create_task`` and answered 202 would no longer hold the
    request open, which is the fact the refusal rests on.
    """
    for await_node in ast.walk(node):
        if not isinstance(await_node, ast.Await):
            continue
        call = await_node.value
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == attr
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == owner
        ):
            return True
    return False


def _unthreaded_window_calls(tree: ast.Module) -> list[int]:
    """Line numbers where ``sustained_busy`` is *called* outside a thread.

    ``asyncio.to_thread(sustained_busy, slot)`` passes it as a reference
    and never calls it, so it trips nothing; the lambda form calls it
    inside the ``to_thread`` call and is exempted by descent.  Anything
    else is a blocking window on the event loop.
    """
    sheltered: set[ast.AST] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "to_thread"
        ):
            sheltered.update(ast.walk(node))

    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or node in sheltered:
            continue
        func = node.func
        named = (isinstance(func, ast.Name) and func.id == WINDOW) or (
            isinstance(func, ast.Attribute) and func.attr == WINDOW
        )
        if named:
            hits.append(node.lineno)
    return hits


class TestBothInvocationClassesReachTheGate:
    """The premise of the refusal: one gate, two answers.

    Each half is asserted separately.  Together they say the gate cannot
    answer ``sustained_busy``'s question for every one of its
    invocations, which is the library's own condition for keeping the
    single read.
    """

    @pytest.mark.parametrize("review_module,_router", REVIEW_GATES)
    def test_the_weekly_job_is_still_the_waiterless_invocation(
        self, review_module: str, _router: str
    ):
        node = _function(_tree(review_module), JOB_ENTRY_POINT)
        called = [
            call
            for call in ast.walk(node)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == GATED_CALL
        ]
        assert called, (
            f"{review_module}.{JOB_ENTRY_POINT} no longer calls {GATED_CALL} — "
            "the waiterless half of the population has moved"
        )

    @pytest.mark.parametrize("review_module,router_module", REVIEW_GATES)
    def test_a_post_route_holds_a_request_open_across_it(
        self, review_module: str, router_module: str
    ):
        router_tree = _tree(router_module)
        alias = _alias_for(router_tree, review_module)
        holders = [
            node.name
            for node in ast.walk(router_tree)
            if isinstance(node, ast.AsyncFunctionDef)
            and _is_post_route(node)
            and _awaits_attribute_call(node, alias, GATED_CALL)
        ]
        assert holders, (
            f"no POST route in {router_module} awaits {alias}.{GATED_CALL} "
            "inline — if every invocation is now waiterless, re-read "
            "estate ADR-0074 §2: the window becomes the intended use"
        )


class TestTheGateIsStillTheSingleRead:
    def test_generate_reads_once_and_does_not_open_a_window(self):
        """Provenance, not behaviour: which symbol the gate is spelled with.

        Only the source can answer this.  Both symbols raise nothing on
        an idle GPU, so a behavioural test passes against either.
        """
        tree = _tree("sysadmin.core.llm_client")
        node = _function(_tree("sysadmin.core.llm_client"), "generate")
        called = {
            call.func.id
            for call in ast.walk(node)
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        }
        assert SINGLE_READ in called
        assert WINDOW not in called
        assert not _unthreaded_window_calls(tree)


class TestAnAdoptedWindowMustGoThroughAThread:
    """Pre-staged: empty population today, and it says so.

    The sweep alone would pass over a package that imports nothing —
    a constant observation is not evidence — so the detector is driven
    at both readings of the adoption it exists to judge.
    """

    def test_no_module_calls_the_window_on_the_event_loop(self):
        offenders = {
            path.relative_to(PACKAGE_ROOT).as_posix(): lines
            for path in sorted(PACKAGE_ROOT.rglob("*.py"))
            if (lines := _unthreaded_window_calls(ast.parse(path.read_text())))
        }
        assert not offenders, (
            f"{WINDOW} blocks on time.sleep and every call site here runs "
            f"inside an event loop: {offenders}"
        )

    def test_the_detector_catches_a_bare_adoption(self):
        source = ast.parse(
            "from estate.gpu import sustained_busy\n"
            "async def generate():\n"
            "    busy = sustained_busy('0000:03:00.0')\n"
        )
        assert _unthreaded_window_calls(source) == [3]

    def test_the_detector_passes_a_threaded_adoption(self):
        source = ast.parse(
            "import asyncio\n"
            "from estate.gpu import sustained_busy\n"
            "async def generate():\n"
            "    busy = await asyncio.to_thread(sustained_busy, '0000:03:00.0')\n"
            "    other = await asyncio.to_thread(lambda: sustained_busy('x'))\n"
        )
        assert _unthreaded_window_calls(source) == []


class TestTheWaiterlessInvocationTakesALease:
    """``SNAG-SCHED-003`` — the job parks instead of reading the card.

    The three assertions are separate because the three failures are:
    a job that stops asking, a job that asks and then reads the counter
    anyway, and a job that never gives the card back.
    """

    @pytest.mark.parametrize("review_module,_router", REVIEW_GATES)
    def test_it_acquires_one(self, review_module: str, _router: str):
        node = _function(_tree(review_module), JOB_ENTRY_POINT)
        names = {
            call.func.id
            for call in ast.walk(node)
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        }
        assert LEASE_ACQUIRE in names, (
            f"{review_module}.{JOB_ENTRY_POINT} no longer takes a GPU lease — "
            "it is back to reading the card once inside the drain's hold, which "
            "costs a narrative every Monday and says nothing about why"
        )

    @pytest.mark.parametrize("review_module,_router", REVIEW_GATES)
    def test_it_tells_the_client_it_holds_one(self, review_module: str, _router: str):
        """Provenance, not behaviour.

        A job that acquired a lease and then let ``generate_review``
        default ``gpu_lease_held`` to ``False`` would wait for the card
        and *then* give up on it — strictly worse than not waiting, and
        green in every behavioural test, because both paths store a
        review.
        """
        node = _function(_tree(review_module), JOB_ENTRY_POINT)
        passed = [
            kw
            for call in ast.walk(node)
            if isinstance(call, ast.Call)
            for kw in call.keywords
            if kw.arg == HELD_FLAG
        ]
        assert passed, (
            f"{review_module}.{JOB_ENTRY_POINT} takes a lease and does not pass "
            f"{HELD_FLAG} — it would wait for the card and then defer on it"
        )

    @pytest.mark.parametrize("review_module,_router", REVIEW_GATES)
    def test_it_releases_in_a_finally(self, review_module: str, _router: str):
        """A lease held to its deadline blocks every other consumer on
        the box for the whole hold, and the arbiter's expiry is the
        backstop rather than the design."""
        node = _function(_tree(review_module), JOB_ENTRY_POINT)
        released = [
            call
            for handler in ast.walk(node)
            if isinstance(handler, ast.Try)
            for call in ast.walk(ast.Module(body=handler.finalbody, type_ignores=[]))
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == LEASE_RELEASE
        ]
        assert released, (
            f"{review_module}.{JOB_ENTRY_POINT} does not release its lease from a "
            "finally — a generation that raises would hold the card until the "
            "arbiter's hold deadline expired it"
        )
