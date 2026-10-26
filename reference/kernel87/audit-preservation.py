from pathlib import Path
import hashlib, json, subprocess

K = Path('/home/cy122/x2pro-linux/linux')
I = Path('/home/cy122/x2pro-linux/initramfs')
O = Path('/mnt/e/edk2-samurai-out/kernel87')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = json.loads((O / 'preserved-before.json').read_text())
changed = {'drivers/gpu/drm/msm/disp/dpu1/dpu_encoder.c',
           'drivers/gpu/drm/msm/disp/dpu1/dpu_trace.h'}
sources = {}
for rel, record in before['sources'].items():
    p = K / rel
    now = {'sha256': sha(p), 'mode': p.stat().st_mode & 0o777}
    assert now['mode'] == record['mode'], rel
    if rel not in changed:
        assert now == record, rel
    else:
        assert now['sha256'] != record['sha256'], rel
    sources[rel] = now
for rel, record in before['initramfs_files'].items():
    p = I / rel
    assert {'sha256': sha(p), 'mode': p.stat().st_mode & 0o777} == record, rel
for rel, target in before['initramfs_links'].items():
    assert str((I / rel).readlink()) == target, rel
assert sha(K / '.config') == before['config_sha256']
assert sha(K / 'usr/initramfs_data.cpio') == before['cpio_sha256']
assert subprocess.check_output(['git', '-C', str(K), 'rev-parse', 'HEAD'], text=True).strip() == before['source_head_local']
image = O / 'Image-watchdog'
assert image.read_bytes()[56:60] == b'ARM\x64'
assert b'#88 SMP PREEMPT' in image.read_bytes()
assert b'7.3.0-rc6-rmx1931-samurai+' in image.read_bytes()
subprocess.run(['git', '-C', str(K), 'apply', '--reverse', '--check',
                '/mnt/e/RealmeX2Pro edk2/reference/kernel87/dpu-frame-watchdog-lifecycle.patch'], check=True)
test = json.loads((O / 'watchdog-test-results.json').read_text())
assert test['audit'] == 'PASS' and test['results']['baseline']['exit'] == 1
assert test['results']['patched']['exit'] == 0
assert test['results']['patched']['output'].count('PASS ') == 6
assert 'warning:' not in (O / 'build-watchdog.log').read_text()
result = {'audit': 'PASS', 'scope': 'build and source preservation; no hardware deployment',
          'sources': sources, 'changed_source_paths': sorted(changed),
          'initramfs_file_count': len(before['initramfs_files']),
          'initramfs_link_count': len(before['initramfs_links']),
          'config_sha256': before['config_sha256'], 'cpio_sha256': before['cpio_sha256'],
          'local_kernel_head': before['source_head_local'],
          'candidate': {'kernel_build_version': 88, 'bytes': image.stat().st_size,
                        'sha256': sha(image), 'deployed': False},
          'build_observed_exit_code': 0, 'regression': test,
          'tests_limit': 'host stubs and deterministic interleavings; no real SMP or handset test'}
(O / 'preservation-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: only two DPU files changed; prior fixes/config/initramfs preserved; #88 unflashed.')
