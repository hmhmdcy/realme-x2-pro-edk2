"""Read-only original k363 input attestation before isolated core Image build."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel456')
spec = importlib.util.spec_from_file_location('storage449', HERE.parent/'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
BUILD = storage.mount.mounted_build()
SOURCE = BUILD.parent/'source354'
COMMIT = 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def run(args):
    return subprocess.check_output(list(map(str, args)), env=ENV, text=True).strip()


def snapshot(root):
    rows = {}
    for path in root.rglob('*'):
        info = path.lstat()
        row = dict(mode=stat.S_IMODE(info.st_mode), uid=info.st_uid, gid=info.st_gid)
        if path.is_symlink():
            row.update(kind='symlink', target=os.readlink(path))
        elif path.is_file():
            row.update(kind='file', sha256=sha(path))
        elif path.is_dir():
            row.update(kind='directory')
        else:
            row.update(kind='special', rdev=info.st_rdev)
        rows[str(path.relative_to(root))] = row
    return rows


def main():
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    record = json.loads((HERE.parent/'kernel363/boot-candidate-build-validation.json').read_text())
    assert record['commit'] == COMMIT and record['terminal']
    image = PRIVATE.parent/'kernel363/Image-k363-private'
    assert sha(image) == record['artifacts']['arch/arm64/boot/Image']['sha256']
    raw = subprocess.check_output([str(SOURCE/'scripts/extract-ikconfig'), str(image)])
    config_hash = hashlib.sha256(raw).hexdigest()
    assert config_hash == record['artifacts']['.config']['sha256']
    (PRIVATE/'config363-from-image-private').write_bytes(raw)
    mapping = dict(line.split('=', 1) for line in raw.decode().splitlines() if line.startswith('CONFIG_'))
    assert mapping['CONFIG_INITRAMFS_SOURCE'] == '"/mnt/samurai-full282/input-initramfs363"'
    assert mapping['CONFIG_LOCALVERSION'] == '"-rmx1931-samurai-k363"'
    assert '# CONFIG_MODULE_SIG is not set' in raw.decode() and mapping['CONFIG_SYSTEM_TRUSTED_KEYS'] == '""'
    original_manifest = json.loads((PRIVATE.parent/'kernel363/boot-initramfs-manifest-private.json').read_text())
    payload = Path(mapping['CONFIG_INITRAMFS_SOURCE'].strip('"'))
    observed = snapshot(payload)
    assert observed == original_manifest, 'Original k363 initramfs input changed'
    (PRIVATE/'initramfs-input-manifest-private.json').write_text(json.dumps(observed, indent=2)+'\n')
    git = lambda *args: run(['git', '-C', SOURCE, *args])
    git('cat-file', '-e', COMMIT+'^{commit}')
    head = git('rev-parse', 'HEAD')
    assert not git('status', '--porcelain')
    source_index = Path(git('rev-parse', '--absolute-git-dir'))/'index'
    shared = {str(BUILD/name): sha(BUILD/name) for name in
              ['.config', 'Module.symvers', 'vmlinux', 'vmlinux.o', 'modules.order', 'arch/arm64/boot/Image',
               'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']}
    shared[str(source_index)] = sha(source_index)
    for name in ['Module.symvers', 'vmlinux', 'modules.order', 'arch/arm64/boot/Image']:
        assert shared[str(BUILD/name)] == record['artifacts'][name]['sha256']
    dtb_matches = shared[str(BUILD/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')] == record['artifacts']['arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']['sha256']
    assert run(['aarch64-linux-gnu-gcc', '--version']).splitlines()[0] == mapping['CONFIG_CC_VERSION_TEXT'].strip('"')
    tools = {name: shutil.which(name) for name in ['make', 'git', 'aarch64-linux-gnu-gcc', 'aarch64-linux-gnu-ld',
             'aarch64-linux-gnu-readelf', 'aarch64-linux-gnu-nm', 'bison', 'flex', 'bc', 'openssl']}
    assert all(tools.values())
    tool_versions = {name: run([name, '--version']).splitlines()[0] for name in
                     ['make', 'aarch64-linux-gnu-gcc', 'aarch64-linux-gnu-ld', 'aarch64-linux-gnu-readelf']}
    sizes = {name: int(run(['du', '-sx', '--block-size=1', BUILD.parent/name]).split()[0])
             for name in ['build', 'source354']}
    disk = shutil.disk_usage(BUILD)
    # Room for independent source/O plus a conservative extra build/link allowance.
    required = sizes['build'] + sizes['source354'] + 2*1024**3 + 2*1024**3
    assert disk.free > required, (disk.free, required)
    details = dict(stage=456, original=record, source=str(SOURCE), build=str(BUILD), shared_before=shared,
                   source_head_before=head, source_index=str(source_index), sizes=sizes,
                   original_initramfs_manifest_sha256=sha(PRIVATE.parent/'kernel363/boot-initramfs-manifest-private.json'),
                   initramfs_source=str(payload), tool_versions=tool_versions,
                   tools=tools, available_layout_tools={name: shutil.which(name) for name in ['gdb', 'gdb-multiarch', 'pahole']},
                   pyelftools_available=importlib.util.find_spec('elftools') is not None,
                   shared_dtb_matches_k363=dtb_matches, dtb_excluded_from_image_target=True,
                   free_bytes=disk.free, required_bytes_including_2gib_reserve=required,
                   source_epoch=int(git('show', '-s', '--format=%ct', COMMIT)))
    (PRIVATE/'preflight-private.json').write_text(json.dumps(details, indent=2)+'\n')
    report = dict(stage=456, commit=COMMIT, original_image_sha256=sha(image), config_sha256=config_hash,
                  original_initramfs_entries=len(observed), original_initramfs_manifest_matches=True,
                  same_gcc_version=True, module_signing_disabled=True, trusted_keys_empty=True,
                  certificate_input_not_required=True, existing_tools_available=True,
                  shared_dtb_matches_k363=dtb_matches, dtb_rebuilt_or_used=False,
                  available_layout_tools=details['available_layout_tools'], pyelftools_available=details['pyelftools_available'],
                  free_bytes=disk.free, cache_sizes=sizes, required_bytes_including_2gib_reserve=required,
                  shared_inputs_read_only=True, phone_or_sdk_accessed=False, passed=True)
    (HERE/'preflight-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
