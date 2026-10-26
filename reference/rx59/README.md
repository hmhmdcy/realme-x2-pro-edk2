# RX59 — joint capture and forced odd-IN reopen

See [session 59](../../sessions/59-joint-capture-and-forced-odd-reopen-gap.md).
Two authorized, bounded runs; all handles/helpers/temporary values restored.

The first run has three complete first TX statuses, with one initial RX retry.
The second forces 75 short IN frames / two short OUT before an ordinary reopen;
first RX sync succeeds but TX seq12407 (`90 04 5b 31 30 30`) is absent.
511 remaining journal records match directly. Raw driver logs, host bytes and
ReceivedCount agree; there is no positive-length failed IN in the matching ETW.
Toggle misalignment is a candidate, not a measured physical DATA0/1 result.

`verify.py` checks frozen hashes, strict frames, logs/counters, snapshot CRCs,
direct cross-owner matching, target-only ETW pairing and status/length order.
Run `python3 verify.py` from either checkout. It performs no device IO.

Raw capture/log bytes are exact. Large target-only XML/JSON uses gzip with
mtime=0; exports.json records both source and compressed hashes. ETL/all-device
XML, PE/PDB, images and mock directories are deliberately kept local. Helpers
remain single-use and must not be re-run against consumed controls/artifacts.

RX58's mistaken 0x1e wording is superseded in focused-research.json and session
58's dated note; old evidence/checksums remain intact. SDK maps 0x1e to host
toggle reset + clear-stall, 0x30 to host reset without toggle reset.
