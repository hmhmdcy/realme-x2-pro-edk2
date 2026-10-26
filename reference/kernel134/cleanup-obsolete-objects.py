from pathlib import Path
import hashlib
import json
import os
import runpy
import struct
import subprocess

r = Path('/mnt/e/RealmeX2Pro edk2')
out = Path('/mnt/e/edk2-samurai-out/kernel134')
assert os.geteuid() == 0
assert not (r / 'reference/kernel134/obsolete-object-cleanup-validation.json').exists()
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
mount = Path('/home/cy122/pmos-samurai-kernel118')
# Reject cleanup while a compiler/linker/build tool is actually running.
for comm in Path('/proc').glob('[0-9]*/comm'):
    try:
        name = comm.read_text().strip()
    except (FileNotFoundError, ProcessLookupError):
        continue
    assert name not in ['make', 'gcc', 'cc1', 'cc1plus', 'ld', 'ld.lld', 'clang', 'rustc'] and not name.startswith('aarch64'), name

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
protected = {}
selected = []
summaries = []
for stage in [120, 121]:
    root = mount / ('camera' + str(stage)) / 'kernel'
    assert root.resolve().is_relative_to(mount.resolve()) and root.is_dir() and not root.is_symlink()
    build = json.loads((r / f'reference/kernel{stage}/kernel-build-validation.json').read_text())
    package = json.loads((r / f'reference/kernel{stage}/package-validation.json').read_text())
    assert build['not_deployed'] and package['not_deployed']
    for name, digest in build['image_and_module_hashes'].items():
        p = root / name
        assert sha(p) == digest
        protected[p] = digest
    private = out.parent / ('kernel' + str(stage))
    assert sha(private / f'Image-k{stage}-private') == build['image_and_module_hashes']['arch/arm64/boot/Image']
    assert sha(private / f'modules-k{stage}-private.tar.gz') == package['archive_sha256']
    source_names = [p.decode() for p in subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).split(b'\0') if p]
    assert not any(name.endswith('.o') for name in source_names)
    for name in source_names:
        p = root / name
        if p.is_file() and not p.is_symlink():
            protected[p] = sha(p)
    for name in ['.config', 'include/config/kernel.release']:
        protected[root / name] = sha(root / name)
    candidates = []
    for p in root.rglob('*.o'):
        if p.is_symlink() or not p.is_file() or '.git' in p.relative_to(root).parts:
            continue
        st = p.stat()
        if st.st_nlink != 1:
            continue
        header = p.open('rb').read(20)
        assert header[:5] == b'\x7fELF\x02' and header[5] == 1
        assert struct.unpack_from('<H', header, 16)[0] == 1
        assert struct.unpack_from('<H', header, 18)[0] in [62, 183]
        assert p.resolve().is_relative_to(root.resolve())
        candidates.append(dict(path=str(p), inode=st.st_ino, device=st.st_dev, size=st.st_size,
                               mtime_ns=st.st_mtime_ns, allocated_bytes=st.st_blocks * 512, sha256=sha(p)))
    assert candidates
    selected.extend(candidates)
    summaries.append(dict(retired_candidate=stage, objects=len(candidates),
                          allocated_bytes=sum(x['allocated_bytes'] for x in candidates),
                          original_sources_config_image_dtb_cpio_and_modules_retained=True,
                          private_image_and_module_archive_hashes_reverified=True))
current = mount / 'power132/kernel'
current_build = json.loads((r / 'reference/kernel132/kernel-build-validation.json').read_text())
for item in current_build['artifacts']:
    if item['role'] == 'Image':
        assert sha(current / 'arch/arm64/boot/Image') == item['sha256']
        protected[current / 'arch/arm64/boot/Image'] = item['sha256']
assert sum(x['allocated_bytes'] for x in selected) > 512 * 1024**2
(out / 'obsolete-object-inventory-private.json').write_text(json.dumps(selected, indent=2) + '\n')
# Only individually identified relocatable .o files in two retired candidates.
for entry in selected:
    p = Path(entry['path'])
    st = p.stat()
    assert (st.st_ino, st.st_dev, st.st_size, st.st_mtime_ns, st.st_nlink) == (
        entry['inode'], entry['device'], entry['size'], entry['mtime_ns'], 1)
    assert sha(p) == entry['sha256']
    p.unlink()
for p, digest in protected.items():
    assert sha(p) == digest, p
assert all(not Path(x['path']).exists() for x in selected)
report = dict(stage=134, candidates=summaries, individually_verified_relocatable_objects_deleted=len(selected),
    allocated_bytes_freed=sum(x['allocated_bytes'] for x in selected),
    source_and_stable_image_hashes_preserved=True, current132_build_unchanged=True,
    only_never_deployed_120_121_object_files_removed=True, original_wsl_vhd_not_resized_or_compacted=True,
    goal_complete=False)
(r / 'reference/kernel134/obsolete-object-cleanup-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
