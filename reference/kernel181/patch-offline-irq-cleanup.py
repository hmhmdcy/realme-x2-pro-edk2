from pathlib import Path
import difflib
import hashlib
import json
import subprocess

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel181')
out.mkdir(parents=True, exist_ok=True)
path = root / 'drivers/mfd/wcd934x.c'
before = path.read_text()
assert hashlib.sha256(before.encode()).hexdigest() == 'dda6b3055b71a46cc8e1680cf776ef66d41c8776e48d1ba6ad2a8fbca4a9b9fb'
backup = out / 'wcd934x.c.before-private'
assert not backup.exists()
backup.write_text(before)
marker = '\tdisable_irq(ddata->irq);\n\n'
assert before.count(marker) == 1
after = before.replace(marker, marker + '''\t/*
\t * The transport is already gone on DOWN. IRQ frees must only update
\t * software state; this map is discarded, never synced back to hardware.
\t * An ordinary driver removal while UP still performs real register I/O.
\t */
\tif (sdev->status == SLIM_DEVICE_STATUS_DOWN)
\t\tregcache_cache_only(ddata->regmap, true);

''')
path.write_text(after)
patch = 'Subject: [PATCH] mfd: wcd934x: isolate offline IRQ cleanup from SLIMbus\n\n'
patch += 'After stopping the parent IRQ, use the existing cache for software\nteardown of an absent codec. Destroy the map without replaying it.\n\n---\n'
patch += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                    fromfile='a/drivers/mfd/wcd934x.c', tofile='b/drivers/mfd/wcd934x.c'))
(ref / 'offline-irq-cleanup.patch').write_text(patch)
check = subprocess.run(['scripts/checkpatch.pl', '--no-tree', '--strict', '--no-signoff', str(ref / 'offline-irq-cleanup.patch')],
                       cwd=root, capture_output=True)
(out / 'checkpatch-private.log').write_bytes(check.stdout + check.stderr)
assert check.returncode == 0, check.stdout.decode()
subprocess.run(['git', 'diff', '--check'], cwd=root, check=True)
(out / 'config-before-private').write_bytes((root / '.config').read_bytes())
print(json.dumps({'stage': 181, 'main_regmap_cache_type_unchanged': True,
                  'offline_mode_only_after_synchronous_parent_irq_stop': True,
                  'source_sha256': hashlib.sha256(after.encode()).hexdigest()}))
