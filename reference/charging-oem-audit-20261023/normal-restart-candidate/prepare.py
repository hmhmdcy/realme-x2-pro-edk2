"""Offline-only generation of review candidates. Never connects to the handset.

The emitted workers are destructive if copied to and explicitly committed on a
handset. They retain the previously validated RESTART2 bootloader sequence;
they do not implement or claim a newly validated plain Linux RESTART path.
"""
from pathlib import Path
import ast
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1] / 'charging-management-20261023'
sha = lambda value: hashlib.sha256(value).hexdigest()

GUARD = r'''
# NEW contract: root supplies a fresh, private R7 transaction guard. This is
# deliberately incompatible with original-private.json / old terminal workers.
import hashlib,re,sys
assert len(sys.argv)==4 and sys.argv[1]=='--guard'
guard_path=Path(sys.argv[2]);assert guard_path.is_absolute()
assert guard_path.is_file() and not guard_path.is_symlink()
assert guard_path.stat().st_uid==0 and not guard_path.stat().st_mode&0o022
meta=json.loads(guard_path.read_text())
assert meta['schema']=='samurai-r7-restart-review-v1'
assert re.fullmatch(r'charging-r7-[a-z0-9-]{8,64}',meta['transaction_id'])
assert meta['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert os.uname().machine=='aarch64'
assert os.uname().release==meta['kernel_release']
assert os.uname().version==meta['kernel_version']
assert os.uname().version.startswith('#363 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert hashlib.sha256(Path('/etc/samurai-rootfs-release').read_bytes()).hexdigest()==meta['rootfs_release_sha256']
module_path='/lib/modules/'+meta['kernel_release']+'/extra/samurai-charging/samurai-usb-input.ko'
manifest_path='/usr/share/samurai-charging/manifest.json'
assert set(meta['disk_pair'])=={module_path,manifest_path}
for name,digest in meta['disk_pair'].items():
 p=Path(name);assert p.is_file() and not p.is_symlink()
 assert p.stat().st_uid==0 and not p.stat().st_mode&0o022
 assert re.fullmatch(r'[0-9a-f]{64}',digest)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
manifest=json.loads(Path(manifest_path).read_text())
assert manifest['release']==meta['kernel_release']
assert manifest['modules']['samurai-usb-input']['target']==module_path
assert manifest['modules']['samurai-usb-input']['sha256']==meta['disk_pair'][module_path]
assert manifest['installed_files'][module_path]==meta['disk_pair'][module_path]
# The disk module is R7, while the current live native provider must still be
# the old accepted R6 module. No unload or replacement is attempted here.
assert hashlib.sha256(Path('/sys/module/samurai_usb_input/notes/.note.gnu.build-id').read_bytes()).hexdigest()==meta['old_loaded_usb_note_sha256']
assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'
r=Path('/var/lib/samurai');o=r/meta['transaction_id']
phase=Path('/run')/(meta['transaction_id']+'-reboot-phase-private.json')
assert not phase.exists()
'''


def replace_one(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def quiesce(base):
    s = replace_one(base, '# Recovery only; source sequence: reference/kernel367/native-quiesce.py\n',
        '# REVIEW CANDIDATE ONLY. New R7 transaction; same validated hardware quiesce.\n')
    s = replace_one(s, '"""Quiesce current297 hardware for a normal Linux reboot; retain camera providers."""',
        '"""Explicit quiesce for one RESTART2 bootloader transition; not run by this audit."""')
    old = "os.umask(0o077);r=Path('/var/lib/samurai');o=r/'charging-20261023-usb-transition';assert not o.exists();o.mkdir(mode=0o700)"
    s = replace_one(s, old, GUARD + "\nassert sys.argv[3]=='--commit-quiesce'\nos.umask(0o077);assert not o.exists();o.mkdir(mode=0o700)")
    old = " boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(json.loads(Path('/root/charging-management-20261023/original-private.json').read_text())['boot_id'] + '\\n').encode() and os.uname().version.startswith('#363 ')"
    s = replace_one(s, old, " boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot.decode().strip()==meta['boot_id']")
    s = replace_one(s, " assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not Path('/run/charging-20261023-usb-reboot-phase-private.json').exists()", " assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not phase.exists()")
    # A service may be marked stopped even when a manual AUTO test ran later.
    # The real stop implementation asserts the synchronous REG08 inhibit.
    s = replace_one(s, " for name in ['samurai-charging'", " command(['/usr/sbin/samurai-charging','stop'])\n for name in ['samurai-charging'")
    s = s.replace("work='charging-usb-dt'", "work='charging-r7-restart',transaction_id=meta['transaction_id'],boot_id=meta['boot_id']")
    return s


def restart(base):
    s = replace_one(base, '# Recovery only; source sequence: reference/kernel367/restart-bootloader.py\n',
        '# REVIEW CANDIDATE ONLY. Fresh current-boot guard; no hot module replacement.\n')
    s = replace_one(s, '"""Single normal Linux restart, following the current297 EUD retirement sequence."""',
        '"""One explicitly committed RESTART2 bootloader transition, followed by host reboot."""')
    old = "r=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(json.loads(Path('/root/charging-management-20261023/original-private.json').read_text())['boot_id'] + '\\n').encode() and os.uname().machine=='aarch64' and os.uname().version.startswith('#363 ')"
    s = replace_one(s, old, GUARD + "\nassert sys.argv[3] in ['--inspect','--commit-restart2-bootloader']")
    s = s.replace("r/'charging-20261023-usb-transition/state-private.json'", "o/'state-private.json'")
    s = s.replace("r/'charging-20261023-usb-transition/summary.json'", "o/'summary.json'")
    s = replace_one(s, "assert s['terminal'] and s['exit_code']==0 and proof['taint']==0", "assert s['terminal'] and s['exit_code']==0 and proof['taint']==0\nassert s['boot_id']==proof['boot_id']==meta['boot_id']\nassert s['transaction_id']==proof['transaction_id']==meta['transaction_id']\nassert (o/'boot-id-private.txt').read_text().strip()==meta['boot_id']")
    s = replace_one(s, "fd=os.open('/dev/mem',os.O_RDWR|os.O_SYNC);rootfd=None;frozen=False;phase=Path('/run/charging-20261023-usb-reboot-phase-private.json');assert not phase.exists()", "if sys.argv[3]=='--inspect':\n print(json.dumps(dict(work='charging-r7-restart',current_boot_guard_pass=True,quiesce_pass=True,restart2_bootloader_expected=True,inspect_only=True,csr_not_read=True)),flush=True);raise SystemExit(0)\nfd=os.open('/dev/mem',os.O_RDWR|os.O_SYNC);rootfd=None;frozen=False")
    old = "  if sys.argv[1:]==['--inspect']:\n   print(json.dumps(dict(work='charging-usb-dt',current_boot_guard_pass=True,quiesce_pass=True,restart2_bootloader_expected=True,eud_csr_low_byte=before&255,inspect_only=True)),flush=True);raise SystemExit(0)\n  assert not sys.argv[1:];rootfd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)"
    s = replace_one(s, old, "  assert sys.argv[3]=='--commit-restart2-bootloader';rootfd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)")
    s = s.replace("work='charging-usb-dt'", "work='charging-r7-restart',transaction_id=meta['transaction_id'],boot_id=meta['boot_id']")
    # Place the exclusive claim before the first mutation, without claiming
    # syscall success merely because a host loses SSH after this marker.
    s = replace_one(s, "  fcntl.ioctl(rootfd,0xc0045877,0);frozen=True", "  with phase.open('x') as claim:json.dump(dict(transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],state='claimed_once',request_count=1),claim)\n  os.sync()\n  fcntl.ioctl(rootfd,0xc0045877,0);frozen=True")
    return s


def main():
    result = {'review_only': True, 'device_access': False, 'workers_executed': False,
              'ordinary_linux_restart_validated': False, 'files': {}}
    for name, transform in [('usb-quiesce.py', quiesce), ('usb-restart.py', restart)]:
        raw = (BASE/name).read_bytes()
        base = raw.decode().replace('\r\n', '\n')
        candidate = transform(base)
        ast.parse(candidate)
        assert 'original-private.json\').read_text' not in candidate
        assert "strip()=='512'" not in candidate
        assert "charging-20261023-usb-transition/" not in candidate
        target = 'r7-quiesce-review.py' if 'quiesce' in name else 'r7-restart-review.py'
        (HERE/target).write_text(candidate, encoding='utf-8', newline='\n')
        (HERE/(target+'.patch')).write_text(''.join(difflib.unified_diff(base.splitlines(True), candidate.splitlines(True), fromfile=name, tofile=target)), encoding='utf-8', newline='\n')
        result['files'][target] = {'source': str(BASE/name), 'source_sha256': sha(raw),
                                   'candidate_sha256': sha(candidate.encode())}
    (HERE/'generation-result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
