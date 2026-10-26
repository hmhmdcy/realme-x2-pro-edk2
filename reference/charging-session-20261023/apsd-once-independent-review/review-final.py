"""Hash-pinned static verification of root's separate bus acknowledgment fix."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] / 'charging-oem-audit-20261023/apsd-once-candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
header = ROOT / 'samurai-apsd-once.h'
assert sha(header) == '78e51238b9155ac7dcd638c32ffd25b487b8983bcad0e6f25cbcaa0f535a4e35'
assert sha(HERE / 'samurai-apsd-once-r1.h') == '7411cbf89f28cd7f97e681023212d52c22c1bb4930a7fe14fd0ac1453952265d'
assert sha(HERE / 'test-r1-ack.c') == '9f014e975b7ed0dfa173beb91091f464f0ad208f2e7c464bcf353e7fffd7bbe3'
text = header.read_text()
body = text.split('static inline int samurai_apsd_write_done(', 1)[1]
assert body.index('samurai_apsd_epoch(s, epoch)') < body.index('if (s->write_ack)')
assert body.index('if (s->write_ack)') < body.index('s->write_ack = 1;')
assert body.index('s->attempted &&') < body.index('s->write_ack = 1;')
assert body.index('s->write_ack = 1;') < body.index('samurai_apsd_clock(s, epoch, now_ms)')
assert 's->write_ack_ms = now_ms;' in body
assert 's->write_error = write_error < 0 ? write_error : write_error ? -EIO : 0;' in body
assert body.index('if (ret)\n\t\treturn ret;', body.index('samurai_apsd_clock')) < body.index('s->phase = SAMURAI_APSD_WAIT_CLEAR;')
clock = text.split('static inline int samurai_apsd_clock(', 1)[1].split('/* A serial', 1)[0]
assert 's->phase == SAMURAI_APSD_FAILED ||\n\t    s->phase == SAMURAI_APSD_CANCELLED' in clock
assert 'now_ms >= s->deadline_ms' in clock
root_result = json.loads((ROOT / 'test-result.json').read_text())
result = {'static_review_passed': True, 'final_header_sha256': sha(header),
          'root_receipt_sha256': sha(ROOT / 'test-result.json'),
          'root_receipt': root_result,
          'old_diagnostic_counterexample_retained': True,
          'same_epoch_one_ack_recorded_before_primary_clock_check': True,
          'old_epoch_second_ack_and_unclaimed_ack_rejected_before_recording': True,
          'timeout_or_cancel_primary_preserved': True,
          'bus_errno_saved_separately': True,
          'new_root_14_or_old_13_groups_rerun': False,
          'root_files_modified': False, 'phone_ssh_sdk_accessed': False}
(HERE / 'final-static-review.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
