#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Does the estate's audit hold a `docs` finding about THIS repository?
#
# SNAG-DOCS-022. estate-manager's `docs` check filed
# `docs:sysadmin_assistant/HANDOFF.md:next_action_not_startable` at 13:55 on
# 2026-09-11 and it reached no sitting at all. `claude-preflight.sh` — the
# script every session here is required to run first — named `:8400`
# nowhere; `~/.claude/hooks/inbox-notice.sh` reads `/api/estate/messages`
# and nothing else; `session-notice.sh` publishes outbound only; and this
# repository's own hourly pull of `/api/audit/findings` filters on
# `JUDGED_AUDIT_CHECKS`, which does not name `docs` and by the ownership
# test must not. The finding was found by a sitting going to look.
#
# estate-manager measured the narrower half (their ADR-0163): where a
# repository has **no sessions**, the estate's "fix it in your own
# repository" direction reaches nobody. This repository has sittings in
# abundance and the finding still arrived nowhere, so a session is the
# necessary condition and not the sufficient one. What was missing here is
# a READER, and this is it.
#
# THIS DOES NOT JUDGE, AND THAT IS THE POINT
# ------------------------------------------
# It prints the producer's own rung — `breach`, `warn`, `info` — verbatim,
# never one of ours. A `warn` about our handoff is advisory where a
# `breach` is not, and translating the rung here would make this repository
# a second author of a severity estate-manager already decided
# (`judge_attention`'s deference to a nudge's rung, at the size of a word).
#
# Nothing here raises an alert, writes a row, or edits a document. Judging
# `docs` in `JUDGED_AUDIT_CHECKS` is REFUSED on ownership and recorded
# there: `ml/Athenaeum/HANDOFF.md` belongs squarely to `ml/Athenaeum`, so
# clause 1 of the admission test fails outright and the population would be
# every repository on the box. A single surviving clause — *nobody says it
# at all* — is a reason to fix the carrier, never to move the judgement.
#
# WHY `docs` AND NOT EVERY CHECK — AND WHY THE CENSUS THAT SAID SO IS GONE
# ------------------------------------------------------------------------
# The obvious widening is "read every finding whose project is us", and
# `ports` is the check it is always proposed for. It is refused, and the
# reason is NOT the one this block carried until 2026-09-14.
#
# What stood here was a census: `Finding(` counted against `"project":`
# across the estate's thirteen check modules on 2026-09-12, reading
# `ports  4 findings, 3 carry detail.project`, and concluding that `docs`
# was the only check whose findings all carry the key. estate-manager
# re-took it over all 1,666 stored findings across 430 runs and **refuted
# the conclusion** (message `a9ee6305`): `ports` is 803 of 929, and the
# 126 misses are one code — `unclaimed_listener`, which by construction
# has no claimant to name, so the absence IS the finding. Every ports code
# that can name a claimant has published the key on every finding it has
# ever filed.
#
# Their measurement is right, and this repository's own had aged too: the
# same walker reads `ports` at SIX sites, FOUR carrying the key, because
# two codes landed on 2026-09-13 (their ADR-0166 and ADR-0168). A census
# of the producer's vocabulary is the wrong instrument to hang a scope on
# — it ages silently, and their ADR-0171 measured the rate at which it
# moves. So the census is RETIRED rather than refreshed, and what replaces
# it is a property that does not move with the vocabulary.
#
# `ports` IS REFUSED BECAUSE A PROJECT-KEYED READER IS WRONG BOTH WAYS
# --------------------------------------------------------------------
# Two ports codes break this reader, one in each direction, and BOTH have
# filed nothing — so neither is visible to any count over `audit_findings`,
# theirs or ours, and the refutation above does not reach either:
#
#   * `claimed_by_an_unregistered_tree` is SEVERITY_BREACH and its detail
#     carries `project`. `JUDGED_AUDIT_CHECKS[ports] = "breach"` already
#     pulls exactly that rung hourly into this box's `alerts` table, and
#     the tray speaks it by name. A project-keyed reader here would catch
#     the same row a second time: one fault, two speakers — the
#     second-owner defect this repository has now found at six scales.
#
#   * `claimed_by_more_than_one_row` is SEVERITY_WARN and names its
#     claimants in `detail.rows[].project`, never in `detail.project`. A
#     reader keyed on `detail.project` is blind to it and CANNOT SAY SO,
#     which is `ports_checked`'s rule — zero-because-blind served as
#     zero-because-clean. It is also the one ports code that can name this
#     repository without naming a port this repository holds.
#
# Note what is true of their sentence and does not reach these two: it is
# quantified over findings EVER FILED, and `claimed_by_more_than_one_row`
# names claimants and has filed nothing, so it sits outside the quantifier
# rather than contradicting it.
#
# `wiring` is out for the first of those reasons alone: `JUDGED_AUDIT_CHECKS`
# carries it at `warn`, and its two file-level codes are a sixth surface
# here (`sysadmin/estate/hook_wiring.py`, ADR-0008).
#
# THE RESIDUE, STATED AS A RULE RATHER THAN A COUNT
# -------------------------------------------------
# Findings about this tree that neither this reader nor
# `JUDGED_AUDIT_CHECKS` carries still reach no sitting, and that residue is
# real and filed rather than absorbed. It is deliberately NOT restated as a
# number: the number is a function of the producer's vocabulary, which is
# the thing just shown to move, and the count this block used to give
# ("eleven checks") could not be reconstructed from its own rule. ADR-0013
# records the decision, its argument, and what would reopen it.
#
# THE KEY IS `detail.project`, NOT THE SUBJECT
# ---------------------------------------------
# `subject` is composed two ways by the same check — `ml/Athenaeum` for a
# repository-level breach and `ml/Athenaeum/HANDOFF.md` for a file-level
# one — so matching on it means re-implementing the producer's
# `f"{subject}/{path}"` composition, which is free to drift from it
# (`judge_queue_invariants`' *the mask is read, never recomputed*).
# `detail.project` is the producer's own statement of whose finding this
# is, and it is uniform across both shapes.
#
# AND THE SPELLING IS THE AUDIT'S, NOT THE REGISTER'S
# ----------------------------------------------------
# This is the single mistake that would ship green and read zero for ever.
# The audit keys on `entry.relative` — the repository's path relative to
# the projects root, `sysadmin_assistant` with an UNDERSCORE. The register
# resolves the same repository to `sysadmin-assistant` with a HYPHEN
# (measured: `filter.receiver.declared` "sysadmin_assistant" →
# `resolved_to` "sysadmin-assistant"), because the register folds every
# spelling it knows and the audit does not. A reader keyed on the register
# spelling matches nothing, for ever, and looks exactly like health.
#
# So the name is DERIVED the way the producer derives it — this checkout's
# real path relative to the projects root — rather than written down. A
# literal would be a second statement of an identity the filesystem
# already holds, and it would be the hyphen the day somebody copied it out
# of a `curl` they had just run.
#
# FAIL OPEN, ON A HARD CLOCK
# --------------------------
# `inbox-notice.sh`'s rule, and its reason restated: `:8400` being down
# must not stall the session opened to fix `:8400`. No jq, no curl, a
# refused connection, a hang, a bad status, a body that is not the
# register's — every one exits SILENTLY.
#
# Silently, but not identically. The exit status separates the three
# answers even where the output cannot:
#
#   0  read, and the estate holds no `docs` finding about this repository
#   1  read, and it holds some — the rows are on stdout
#   2  NOT read, or read blind — stdout is empty or says why
#
# That split is what keeps the fail-open silence from becoming a lie.
# `claude-preflight.sh` renders 2 as "could not be read", never as "none"
# — its own `ports_checked` convention, already written into the open-snag
# section two blocks below where this one is called from.
#
# BLIND INCLUDES A RUN WHOSE `docs` CHECK ERRORED
# ------------------------------------------------
# A run in which `docs` raised publishes no `docs` findings, so the
# obvious reader answers "none" off a check that never looked. `run.checks.docs`
# is consulted for exactly that: absent, or `status: error`, is status 2.
# The status is DERIVED at the producer (`CheckResult.status` returns
# `error` iff `error` is set), so reading it is reading their statement
# rather than re-deciding it.
#
# WHAT IT DELIBERATELY DOES NOT DO
# --------------------------------
#   * It does not age the RUN. A stale audit already has an owner here —
#     `judge_audit_invariants`' `audit_max_age_hours`, which raises a row
#     when the audit has not run. A second reader of that fact is the
#     second-owner defect arriving inside the fix for a missing carrier.
#   * It does not age a FINDING. `standing_days` is printed because the
#     producer publishes it and a sitting wants to know whether this is
#     new; nothing here turns it into a deadline. `inbox-notice.sh`'s
#     refusal, for its reason.
#   * It does not fix, file, close or edit anything. The estate does not
#     fix what it finds, and neither does its reader.
# ---------------------------------------------------------------------------

set -uo pipefail

# Overridable for tests only; the defaults are the live estate.
BASE_URL="${ESTATE_BASE_URL:-http://127.0.0.1:8400}"
PROJECTS_ROOT="${ESTATE_PROJECTS_ROOT:-$HOME/projects}"

# The hard clock, chosen against the thing being protected — a session's
# first breath — rather than against the service's latency.
TIMEOUT="${ESTATE_DOCS_TIMEOUT:-2}"

# How many rows to print in full. The estate has never held more than a
# handful about one repository; a longer list means something has gone
# wrong and the count line says so rather than the banner scrolling.
SHOW=5

command -v jq   >/dev/null 2>&1 || exit 2
command -v curl >/dev/null 2>&1 || exit 2

# --- 1. whose findings are we asking about? --------------------------------
# `entry.relative`, computed the way the registry computes it: the real
# path of this checkout, relative to the projects root. `pwd -P` on both
# sides, because a symlinked checkout compared against an unresolved root
# yields no match and no complaint.
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OWN_ROOT=$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || true)
[[ -n "$OWN_ROOT" ]] || OWN_ROOT=$(cd "$HERE/.." && pwd)

OWN_REAL=$(cd "$OWN_ROOT" 2>/dev/null && pwd -P || printf '%s' "$OWN_ROOT")
ROOT_REAL=$(cd "$PROJECTS_ROOT" 2>/dev/null && pwd -P || printf '%s' "$PROJECTS_ROOT")

case "$OWN_REAL" in
    "$ROOT_REAL"/*) NAME=${OWN_REAL#"$ROOT_REAL"/} ;;
    # Outside the projects root the registry has never heard of this
    # checkout, so there is no relative path to compute. The basename is
    # the only address left and it is the right one for a top-level
    # repository, which is every repository this reader runs in.
    *)              NAME=$(basename "$OWN_REAL") ;;
esac
[[ -n "$NAME" ]] || exit 2

# --- 2. ask ----------------------------------------------------------------
RESP=$(curl -s \
            --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" \
            -w $'\n%{http_code}' \
            "$BASE_URL/api/audit/findings" 2>/dev/null || true)
[[ -n "$RESP" ]] || exit 2

CODE=${RESP##*$'\n'}
BODY=${RESP%$'\n'*}
# 000 is curl's code for "never got a response" — refused, unresolved, or
# the hard timeout biting. All three are the same answer here.
[[ "$CODE" == "200" ]] || exit 2

printf '%s' "$BODY" | jq -e '.findings | type == "array"' >/dev/null 2>&1 || exit 2

# --- 3. did the `docs` check actually look? --------------------------------
# An absent entry and an errored one are both "this run says nothing about
# documents", which is not the same fact as "there is nothing to say".
DOCS_STATUS=$(printf '%s' "$BODY" \
    | jq -r '.run.checks.docs.status // empty' 2>/dev/null || true)
if [[ -z "$DOCS_STATUS" || "$DOCS_STATUS" == "error" ]]; then
    exit 2
fi

# --- 4. what does it hold about us? ----------------------------------------
ROWS=$(printf '%s' "$BODY" | jq -r --arg name "$NAME" --argjson n "$SHOW" '
    [ .findings[]
      | select(.check == "docs")
      | select(.detail.project == $name) ]
    | .[0:$n][]
    | "\(.severity)  \(.fingerprint)  standing \(.standing_days // 0)d\n      \(.summary)"
' 2>/dev/null || true)

COUNT=$(printf '%s' "$BODY" | jq -r --arg name "$NAME" '
    [ .findings[]
      | select(.check == "docs")
      | select(.detail.project == $name) ] | length
' 2>/dev/null || printf '0')
[[ "$COUNT" =~ ^[0-9]+$ ]] || COUNT=0

# A `docs` finding carrying no `detail.project` cannot be attributed to any
# repository, so it can neither be reported as ours nor set aside as
# somebody else's. It is COUNTED rather than dropped: dropping it silently
# is the blind-read-as-clean collapse one level down from the one this
# whole script exists for.
#
# The population is empty by the producer's construction — all 7 of the
# `docs` check's `Finding(` sites pass `detail={"project": subject, …}`,
# measured 2026-09-12 — and `tests/test_estate_docs_notice.py` holds it
# there, so this branch is the guard against that stopping being true
# rather than a case anyone has seen.
ORPHANS=$(printf '%s' "$BODY" | jq -r '
    [ .findings[] | select(.check == "docs") | select(.detail.project == null) ] | length
' 2>/dev/null || printf '0')
[[ "$ORPHANS" =~ ^[0-9]+$ ]] || ORPHANS=0

if [[ "$COUNT" -gt 0 && -n "$ROWS" ]]; then
    printf '%s\n' "$ROWS"
    [[ "$COUNT" -gt "$SHOW" ]] && printf '  … and %s more.\n' "$((COUNT - SHOW))"
    printf '%s\n' "Read them in full:"
    printf "  curl -s '%s/api/audit/findings' | jq '[.findings[] | select(.detail.project==\"%s\")]'\n" \
        "$BASE_URL" "$NAME"
    printf '%s\n' "Fix it in THIS repository under its own ADR process — the estate"
    printf '%s\n' "does not fix what it files, and nothing here has judged it."
    exit 1
fi

if [[ "$ORPHANS" -gt 0 ]]; then
    printf '%s docs finding(s) name no project, so "none for %s" cannot be said.\n' \
        "$ORPHANS" "$NAME"
    exit 2
fi

exit 0
