# Fixed F.10 vendor-only extractor review

Accepted within the frozen source scope. The eight files in author delivery
4639f6b8ceead1fc6aa335f7f938ff38b120706766cc234141428394989a6d5b
and the private plan were hashed without executing the extractor. The existing
five-method/13-case fixture and original default-child receipts match those
source bytes; neither was rerun.

The reviewed path creates an exclusive OUT, checks the fixed ZIP facts and
CRC through EOF, requires Brotli native input consumption and bounded exact
output, then reconstructs a new 1711276032-byte host image from exactly
1613049856 new-data bytes with global nonoverlap/coverage validation. The
original Node child is waited in a finally block. Failure retains artifacts
and cannot replay the same OUT. Sources and cached inputs are opened readonly.

This is source readiness for one later host-only extraction. No real vendor
payload, filesystem, descriptor or pack identity has been validated. Whole-OTA
SHA/signature and generic unknown-OTA support are outside this result.
