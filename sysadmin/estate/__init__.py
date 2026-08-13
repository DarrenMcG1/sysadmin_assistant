"""Judging the estate's published surfaces from outside.

The estate manager holds project state, runs the conformance audit and
arbitrates the GPU queue; by its ADR-0003 and ADR-0004 §6 it **publishes
and never acts** — it files findings, it never alerts, and it never
grades its own scan.  Something outside it has to read those numbers and
decide whether they wake a human.  That is this package, and it is the
half of the Session 4 cutover that stayed behind: until it ran, the
estate computed idle nudges every night and no toast ever appeared.

Three modules, in the order data moves through them:

- :mod:`sysadmin.estate.client` — pulls the four surfaces over HTTP.
  Knows about timeouts and unreachability; knows nothing about
  judgement.
- :mod:`sysadmin.estate.judgements` — **pure**: a payload in, a list of
  :class:`~sysadmin.estate.judgements.Judgement` out.  No database, no
  HTTP, no clock beyond what the payload carries.  This is where every
  threshold and every "this is not our business" rule lives, so the
  rules can be tested against a literal without a service running.
- :mod:`sysadmin.estate.agent` — the lifecycle: raise what is new,
  resolve what has gone, and write neither when the surface could not
  be read.
"""
