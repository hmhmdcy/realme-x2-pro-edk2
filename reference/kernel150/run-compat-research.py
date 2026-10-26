"""Bounded stock-Mesa process experiments; keep raw logs on the device."""
from pathlib import Path
import hashlib, json, os, re, signal, subprocess, time

os.umask(0o077)
base = Path('/var/lib/samurai/k150-research')
base.mkdir(mode=0o700, exist_ok=True)
sdk = Path('/tmp/k148-sdk')
gccdir = next((sdk/'usr/lib/gcc').glob('aarch64-*/*'))
compiler_env = dict(os.environ, PATH=str(sdk/'usr/bin')+':'+os.environ['PATH'],
                    LD_LIBRARY_PATH=str(sdk/'usr/lib')+':'+str(sdk/'lib'))
common = [str(sdk/'usr/bin/gcc'), '--sysroot='+str(sdk), '-B'+str(gccdir)+'/',
          '-B'+str(sdk/'usr/bin')+'/', '-O2', '-Wall', '-Wextra', '-Werror']
with (base/'compile-private.log').open('wb') as log:
    subprocess.run(common+['-shared', '-fPIC', str(base/'iova-compat-tap.c'),
                           '-ldl', '-o', str(base/'iova-compat-tap.so')],
                   env=compiler_env, stdout=log, stderr=subprocess.STDOUT, check=True)
    subprocess.run(common+[str(base/'vulkan-capabilities.c'), '-L/usr/lib',
                           '-l:libvulkan.so.1', '-o', str(base/'vulkan-capabilities')],
                   env=compiler_env, stdout=log, stderr=subprocess.STDOUT, check=True)
original = Path('/var/lib/samurai/k149-deployment/libvulkan_freedreno.so.original')
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(original) == 'c72f5ee34e9f4fcf200e4987285f6fdfef4442fd146b77a4c0d1cbf5d5525955'
icd = base/'stock-icd.json'
icd.write_text(json.dumps(dict(file_format_version='1.0.1', ICD=dict(
    api_version='1.4.354', library_arch='64', library_path=str(original)))))
protected = [Path('/usr/lib/libvulkan_freedreno.so'), Path('/lib/apk/db/installed'),
             Path('/etc/greetd/samurai-phosh.toml')]
hashes_before = {str(p): digest(p) for p in protected}
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
(base/'boot-id-private.txt').write_bytes(boot)
def counts():
    text = subprocess.check_output(['dmesg'], text=True)
    return {k: text.count(v) for k, v in dict(gpu_faults='gpu fault:', warnings='WARNING:',
        dpu_timeouts='frame done timeout', dsi_errors='dsi_err_worker',
        dma_prepare='unable to prepare channel').items()}
def desktop():
    result = {}
    for name in ['phoc', 'phosh']:
        found = subprocess.run(['pgrep', '-x', name], capture_output=True, text=True)
        pids = []
        for pid in found.stdout.split():
            try:
                status = (Path('/proc')/pid/'status').read_text()
                if int(re.search(r'^Uid:\s+(\d+)', status, re.M)[1]) == 10000:
                    pids.append(pid)
            except FileNotFoundError:
                pass
        result[name] = sorted(pids)
    return result
before, pids = counts(), desktop()
assert all(pids.values()) and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
results = []
def experiment(label, command, kernel_iova=True, pause_ms=0):
    out = base/label
    out.mkdir(mode=0o700)
    env = dict(os.environ, VK_DRIVER_FILES=str(icd),
        LD_PRELOAD=str(base/'iova-compat-tap.so'), K150_IOCTL_LOG=str(out/'ioctl-private.jsonl'),
        K149_HOLES='1', K148_VARIANTS='1', K148_DRAW_CHURN='1',
        K148_PHONE_LAYOUT='1', K148_PAUSE_MS=str(pause_ms), TU_DEBUG='gmem',
        XDG_RUNTIME_DIR='/run/user/10000', WAYLAND_DISPLAY='wayland-0')
    if kernel_iova: env['K150_KERNEL_IOVA'] = '1'
    else: env.pop('K150_KERNEL_IOVA', None)
    with (out/'stdout-private.log').open('wb') as log:
        child = subprocess.Popen(command, env=env, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try: code = child.wait(timeout=90)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try: child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=3)
            raise
    rows = [json.loads(s) for s in (out/'ioctl-private.jsonl').read_text().splitlines()]
    addresses = [r for r in rows if r['kind'] == 'gem_info' and r['selector'] == 1 and r['rc'] == 0]
    result = dict(label=label, exit=code, kernel_iova_simulated=kernel_iova,
        en_vm_bind_rejected=sum(r['blocked'] for r in rows if r['kind'] == 'set_param' and r['selector'] == 0x16),
        va_start_rejected=sum(r['blocked'] for r in rows if r['kind'] == 'get_param' and r['selector'] == 0x0e),
        va_size_success=sum(r['rc'] == 0 for r in rows if r['kind'] == 'get_param' and r['selector'] == 0x0f),
        vm_bind_calls=sum(r['kind'] == 'vm_bind' for r in rows),
        set_iova_calls=sum(r['kind'] == 'gem_info' and r['selector'] == 4 for r in rows),
        get_iova_calls=len(addresses), unaligned_get_iova=sum(r['value'] % 65536 != 0 for r in addresses))
    text = (out/'stdout-private.log').read_text()
    if label.endswith('capabilities'):
        result['features'] = json.loads(next(s for s in text.splitlines() if s.startswith('{')))
    else:
        pixels = re.findall(r'^PIXEL iteration=.*$', text, re.M)
        result['pixel_result_lines'] = len(pixels)
        result['pixel_mismatches'] = sum(int(re.search(r'mismatches=(\d+)', s)[1]) for s in pixels)
        result['pixels_verified'] = int(re.search(r'ALL_PIXELS_PASS iterations=\d+ pixels=(\d+)', text)[1])
        result['pixel_log_tail'] = text.splitlines()[-2:]
        assert len(pixels) == int(command[-1]) and result['pixel_mismatches'] == 0
    results.append(result)
    assert code == 0, label
    assert result['en_vm_bind_rejected'] > 0
    if kernel_iova:
        assert result['va_start_rejected'] > 0
        assert result['vm_bind_calls'] == result['set_iova_calls'] == 0
        assert result['unaligned_get_iova'] == 0
    print(json.dumps(result), flush=True)

experiment('vm-bind-only-capabilities', [str(base/'vulkan-capabilities')], kernel_iova=False)
experiment('kernel-iova-capabilities', [str(base/'vulkan-capabilities')])
experiment('stock-gmem-holes', ['/var/lib/samurai/k149-tools/vulkan-hole-probe', '18'], pause_ms=1100)
deadline = time.monotonic()+60
while time.monotonic() < deadline: time.sleep(0.2)
after = counts()
report = dict(stock_library_sha256=digest(original), mesa_modified=False,
    kernel_modified=False, capability_failures_simulated_in_process=True, tests=results,
    before=before, after=after, new_gpu_faults=after['gpu_faults']-before['gpu_faults'],
    delayed_observation_seconds=60, desktop_preserved=desktop() == pids,
    boot_preserved=Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot,
    protected_files_preserved=hashes_before == {str(p): digest(p) for p in protected},
    taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    pending_devcoredumps=len(list(Path('/sys/class/devcoredump').glob('devcd*'))))
(base/'result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
assert before == after and report['desktop_preserved'] and report['boot_preserved']
assert report['protected_files_preserved'] and report['taint'] == 0 and report['pending_devcoredumps'] == 0
