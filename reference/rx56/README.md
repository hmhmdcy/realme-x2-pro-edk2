# RX56: exact pre-buffer source boundaries and focused research

2026-10-10. See [session 56](../../sessions/56-source-boundaries-and-focused-research.md)
for the repair/measurement distinction, new versus reused search results, and
the next discriminating observation. No phone/driver/registry change or port
open this session. RX55's actual TX gap/startup missing receipt remain unresolved.

Selected exact installed-driver disassemblies plus identities verify the reset
selector, ReadIrpCompletion, conditional raw logger and padding exclusion.
QCSER_Open/ReadThread and accepted-buffer function are existing RX54 dependencies.
Executed audit/state helpers are byte-identical; derived text is UTF-8 LF and
disassembly trailing formatting spaces are trimmed. exports.json records both
hashes. Old target-only ETW metadata is losslessly gzipped; no payload/PID exists.
source-manifest.json identifies newly downloaded public sources kept outside Git.
Full sys/PDB, source snapshots and all-device ETL/XML remain local.

Run `python3 verify.py` from this directory. It checks every published hash,
dependency identity, exact code bytes in all selected functions, the earlier
489-byte ETW/raw total, read-only registry/state and unchanged candidate.
It does not claim runtime branch selection, physical ACK/toggle or a repair.
The executed source-audit helpers retain their original external paths; rerun
them only with the original local PE/PDB/source inputs, not against guessed files.
