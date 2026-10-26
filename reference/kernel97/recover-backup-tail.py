from pathlib import Path
import hashlib, json, re
out = Path('/mnt/e/edk2-samurai-out/kernel97')
sha = lambda data: hashlib.sha256(data).hexdigest()
partial = (out / 'logdump-before.img').read_bytes()
tail = (out / 'logdump-tail-retry1.bin').read_bytes()
assert len(partial) == 67092480 and len(tail) == 16384
record = (out / 'backup-tail-retry1.log').read_text(encoding='utf-8-sig')
assert sha(tail) in record and sha(partial) in record
expected = '226c4da4c28953c394e9677af069e48c3cad0f036f922ea47712b762761c8722'
data = partial + tail
assert len(data) == 67108864 and sha(data) == expected
assert sha((out / 'boot-partition-before.img').read_bytes()) == 'a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7'
with (out / 'logdump-before-recovered.img').open('xb') as target:
    target.write(data)
report = dict(partial_bytes=len(partial), recovered_tail_bytes=len(tail),
              device_prefix_and_tail_hashes_verified=True, full_source_sha256_verified=True,
              complete_logdump_sha256=expected, failed_transfer_copy_preserved=True)
(out / 'backup-recovery-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
