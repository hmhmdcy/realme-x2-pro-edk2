"""Finish the local documentation checks without committing or publishing."""
from pathlib import Path
import ast
import hashlib
import json
import shutil
import subprocess

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel145'
out = Path('/mnt/e/edk2-samurai-out/kernel145')
mirror = Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
backup = out / 'docs-before-closeout-private'
mirror_backup = out / 'mirror-before-closeout-private'
assert not (out / 'closeout-final-validation.json').exists()
for name in ['linux-port/docs/ROOTFS-F2FS-IMAGE.md', 'linux-port/docs/ROOTFS-PRESERVE-ANDROID.md']:
    path = root / name
    saved = backup / name.replace('/', '--')
    assert not saved.exists()
    shutil.copyfile(path, saved)
    dest = mirror / name
    if dest.exists():
        previous = mirror_backup / name
        assert not previous.exists()
        previous.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(dest, previous)
    head, rest = path.read_text().split('\n', 1)
    path.write_text(head + '\n\n当前状态以[阶段145部署与收尾](../../sessions/145-dsi-deployment-and-session-closeout.md)和[下一轮检查点](../../NEXT-SESSION.md)为准：持久F2FS系统132已在手机运行，当前内核145；本轮只刷logdump，没有重刷userdata。下方“未部署/未安装rootfs”等描述属于此前方案或离线构建阶段，不是当前状态。\n' + rest)
    shutil.copyfile(path, dest)
    assert path.read_bytes() == dest.read_bytes()

# Include this finalizer in the reviewed local reference copy.
for path in ref.glob('*.py'):
    ast.parse(path.read_text())
    dest = mirror / 'reference/kernel145' / path.name
    if not dest.exists() or path.read_bytes() != dest.read_bytes():
        assert not dest.exists(), 'Unexpected post-sync public script modification'
        shutil.copyfile(path, dest)
health = subprocess.run(['bash', str(root / 'linux-port/scripts/docs-health-check.sh')],
                        capture_output=True, timeout=60)
out.joinpath('docs-health-closeout-final-private.txt').write_bytes(health.stdout + health.stderr)
assert health.returncode == 0 and b'RESULT: clean' in health.stdout, 'Documentation health check failed'
for name in ['documentation-validation.json', 'closeout-validation.json']:
    path = ref / name
    data = json.loads(path.read_text())
    data.update(mirror_sync_pending=False, documentation_checks_pending=False,
                local_mirror_byte_identical=True, documentation_health_clean=True,
                new_handover_links_verified=True, private_archives_manifest_verified=True,
                preexisting_rootfs_document_drift_resolved=True,
                docs_checker_scans_markdown_only=True,
                baseline_display_radio_traces_preserved=True,
                existing_edk2_dtb_modification_preserved=True,
                committed=False, pushed=False, published=False)
    path.write_text(json.dumps(data, indent=2) + '\n')
    shutil.copyfile(path, mirror / 'reference/kernel145' / name)

names = ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'HANDOVER-NEXT.md', 'HANDOVER.md',
         'README.md', 'DOCS-INDEX.md', 'linux-port/README.md',
         'linux-port/docs/HARDWARE-STATUS.md', 'linux-port/docs/00-INDEX.md',
         'linux-port/docs/ROOTFS-F2FS-IMAGE.md', 'linux-port/docs/ROOTFS-PRESERVE-ANDROID.md',
         'linux-port/scripts/docs-health-check.sh',
         'sessions/145-dsi-observation-and-old-build-cleanup.md',
         'sessions/145-dsi-deployment-and-session-closeout.md']
names += [str(p.relative_to(root)) for p in ref.iterdir() if p.is_file()]
for name in names:
    assert (root / name).read_bytes() == (mirror / name).read_bytes(), name
checksums = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sorted(names)}
out.joinpath('closeout-public-files-private.sha256').write_text(''.join(
    digest + '  ' + name + '\n' for name, digest in checksums.items()))
report = dict(stage=145, current_phone_kernel=145, current_software_generation=132,
    runtime_and_cleanup_archives_verified=True, temporary_recorder_closed=True,
    current_docs_and_handover_complete=True, documentation_health_clean=True,
    public_files_byte_identical=True, verified_public_files=len(names),
    private_images_and_credentials_not_copied=True,
    no_new_hardware_accepted=True, committed=False, pushed=False,
    session_closed_at_user_request=True, goal_complete=False)
out.joinpath('closeout-final-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
