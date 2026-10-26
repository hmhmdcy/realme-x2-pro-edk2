"""Check legal nonzero image offsets and untouched prefix data with stock Mesa."""
from pathlib import Path
import hashlib, json, os, re, signal, subprocess, time

os.umask(0o077)
base = Path('/var/lib/samurai/k150-research')
old = Path('/var/lib/samurai/k149-tools/vulkan-hole-probe.c').read_text()
new = old
changes = [
    ('struct image { VkImage image; VkImageView view; VkDeviceMemory mem; };',
     'struct image { VkImage image; VkImageView view; VkDeviceMemory mem; VkDeviceSize prefix; };'),
    (' im.mem=allocate(r,0);CHECK(vkBindImageMemory(dev,im.image,im.mem,0));',
     ''' unsigned factor=(unsigned)atoi(getenv("K150_OFFSET_FACTOR"));
 im.prefix=r.alignment*factor;r.size+=im.prefix;
 printf("IMAGE_BIND alignment=%llu offset=%llu\\n",(unsigned long long)r.alignment,(unsigned long long)im.prefix);
 if(!im.prefix||im.prefix%r.alignment||im.prefix%65536==0)exit(19);
 im.mem=allocate(r,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
 unsigned char *prefix;CHECK(vkMapMemory(dev,im.mem,0,im.prefix,0,(void**)&prefix));
 memset(prefix,0xa5,(size_t)im.prefix);vkUnmapMemory(dev,im.mem);
 CHECK(vkBindImageMemory(dev,im.image,im.mem,im.prefix));'''),
    ('static void free_image(struct image im) {vkDestroyImageView',
     '''static void free_image(struct image im) {
 unsigned char *prefix;CHECK(vkMapMemory(dev,im.mem,0,im.prefix,0,(void**)&prefix));
 unsigned bad=0;for(VkDeviceSize i=0;i<im.prefix;i++)bad+=prefix[i]!=0xa5;
 vkUnmapMemory(dev,im.mem);printf("PREFIX_SENTINEL bytes=%llu mismatches=%u\\n",(unsigned long long)im.prefix,bad);
 if(bad)exit(20);
 vkDestroyImageView'''),
]
for before, after in changes:
    assert new.count(before) == 1, before
    new = new.replace(before, after)
source = base/'suballocation-probe.c'
source.write_text(new)
sdk = Path('/tmp/k148-sdk')
gccdir = next((sdk/'usr/lib/gcc').glob('aarch64-*/*'))
compiler_env = dict(os.environ, PATH=str(sdk/'usr/bin')+':'+os.environ['PATH'],
    LD_LIBRARY_PATH=str(sdk/'usr/lib')+':'+str(sdk/'lib'))
with (base/'suballocation-compile-private.log').open('wb') as log:
    subprocess.run([str(sdk/'usr/bin/gcc'), '--sysroot='+str(sdk), '-B'+str(gccdir)+'/',
        '-B'+str(sdk/'usr/bin')+'/', '-O2', '-Wall', '-Wextra', str(source),
        '-L/usr/lib', '-l:libvulkan.so.1', '-o', str(base/'suballocation-probe')],
        env=compiler_env, stdout=log, stderr=subprocess.STDOUT, check=True)
def counts():
    text = subprocess.check_output(['dmesg'], text=True)
    return {k: text.count(v) for k, v in dict(gpu_faults='gpu fault:', warnings='WARNING:',
        dpu_timeouts='frame done timeout', dsi_errors='dsi_err_worker',
        dma_prepare='unable to prepare channel').items()}
protected = [Path('/usr/lib/libvulkan_freedreno.so'), Path('/lib/apk/db/installed'),
             Path('/etc/greetd/samurai-phosh.toml')]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
hashes = {str(p): digest(p) for p in protected}
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
before = counts()
saved = set()
def collect_cores():
    for core in Path('/sys/class/devcoredump').glob('devcd*'):
        if core.name in saved: continue
        with (base/(core.name+'-suballocation-private.data')).open('wb') as out:
            subprocess.run(['cat', str(core/'data')], stdout=out, check=True, timeout=20)
        saved.add(core.name)
tests = []
for factor in [1, 2, 15]:
    out = base/('suballocation-'+str(factor))
    out.mkdir(mode=0o700)
    env = dict(os.environ, VK_DRIVER_FILES=str(base/'stock-icd.json'),
        LD_PRELOAD=str(base/'iova-compat-tap.so'), K150_IOCTL_LOG=str(out/'ioctl-private.jsonl'),
        K150_KERNEL_IOVA='1', K150_OFFSET_FACTOR=str(factor), K149_HOLES='1',
        K148_VARIANTS='1', K148_DRAW_CHURN='1', TU_DEBUG='gmem',
        XDG_RUNTIME_DIR='/run/user/10000', WAYLAND_DISPLAY='wayland-0')
    started = time.monotonic()
    with (out/'stdout-private.log').open('wb') as log:
        child = subprocess.Popen([str(base/'suballocation-probe'), '6'], env=env,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        while child.poll() is None:
            collect_cores()
            if time.monotonic()-started > 60:
                os.killpg(child.pid, signal.SIGTERM)
                try: child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=3)
                break
            time.sleep(0.1)
    text = (out/'stdout-private.log').read_text()
    rows = re.findall(r'^PIXEL iteration=.*$', text, re.M)
    sentinels = re.findall(r'^PREFIX_SENTINEL bytes=(\d+) mismatches=(\d+)', text, re.M)
    bind = re.findall(r'^IMAGE_BIND alignment=(\d+) offset=(\d+)', text, re.M)
    summary = re.search(r'ALL_PIXELS_PASS iterations=(\d+) pixels=(\d+)', text)
    calls = [json.loads(s) for s in (out/'ioctl-private.jsonl').read_text().splitlines()]
    result = dict(offset_factor=factor, exit=child.returncode, pixel_rows=len(rows),
        pixels_verified=int(summary[2]) if summary else 0,
        pixel_mismatches=sum(int(re.search(r'mismatches=(\d+)', s)[1]) for s in rows),
        prefix_bytes_checked=sum(int(n) for n, _ in sentinels),
        prefix_mismatches=sum(int(n) for _, n in sentinels),
        image_bindings=len(bind), image_alignments=sorted({int(a) for a, _ in bind}),
        image_offsets=sorted({int(b) for _, b in bind}),
        vm_bind_calls=sum(r['kind'] == 'vm_bind' for r in calls),
        set_iova_calls=sum(r['kind'] == 'gem_info' and r['selector'] == 4 for r in calls),
        after=counts())
    tests.append(result)
    print(json.dumps(result), flush=True)
    if child.returncode != 0 or not summary or counts() != before: break
deadline = time.monotonic()+60
while time.monotonic() < deadline:
    collect_cores(); time.sleep(0.2)
report = dict(stock_mesa=True, process_capability_simulation=True, tests=tests,
    before=before, after=counts(), core_saved=len(saved), delayed_observation_seconds=60,
    boot_preserved=Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot,
    protected_files_preserved=hashes == {str(p): digest(p) for p in protected},
    taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    total_pixels=sum(r['pixels_verified'] for r in tests),
    total_prefix_bytes=sum(r['prefix_bytes_checked'] for r in tests))
(base/'suballocation-result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
assert len(tests) == 3 and all(r['exit'] == 0 and r['pixel_rows'] == 6 for r in tests)
assert all(r['pixel_mismatches'] == r['prefix_mismatches'] == 0 for r in tests)
assert report['after'] == before and report['taint'] == 0 and report['core_saved'] == 0
assert report['boot_preserved'] and report['protected_files_preserved']
