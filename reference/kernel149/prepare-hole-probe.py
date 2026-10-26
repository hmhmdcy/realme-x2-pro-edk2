"""Build a pixel regression with unmapped holes before color allocations."""
from pathlib import Path
import difflib, hashlib, json, os, subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k149-tools')
out.mkdir(mode=0o755, exist_ok=True)
source = Path('/var/lib/samurai/k148-tools/uploaded-sources/k148-vulkan-pixel-probe.c')
old = source.read_text()
new = old
changes = [
    (' unsigned variants=getenv("K148_VARIANTS")?atoi(getenv("K148_VARIANTS")):0;',
     ' unsigned holes=getenv("K149_HOLES")?atoi(getenv("K149_HOLES")):0;\n unsigned variants=getenv("K148_VARIANTS")?atoi(getenv("K148_VARIANTS")):0;'),
    ('  struct buffer readback=buffer(',
     '  if(holes){CHECK(vkDeviceWaitIdle(dev));for(unsigned i=0;i<7;i++)free_buffer(churn[i]);}\n  struct buffer readback=buffer('),
    ('  for(unsigned i=0;i<7;i++)vkCmdFillBuffer(',
     '  if(!holes)for(unsigned i=0;i<7;i++)vkCmdFillBuffer('),
    ('free_image(color);for(unsigned i=0;i<7;i++)free_buffer(churn[i]);',
     'free_image(color);if(!holes)for(unsigned i=0;i<7;i++)free_buffer(churn[i]);'),
    ('fence_ordered_lifetime=1\\n",loops,(unsigned long long)pixels)',
     'fence_ordered_lifetime=1 holes=%u\\n",loops,(unsigned long long)pixels,holes)'),
]
for before, after in changes:
    assert new.count(before) == 1, before
    new = new.replace(before, after)
probe = out/'vulkan-hole-probe.c'
probe.write_text(new)
(out/'hole-probe.patch').write_text(''.join(difflib.unified_diff(
    old.splitlines(True), new.splitlines(True), fromfile='a/vulkan-pixel-probe.c',
    tofile='b/vulkan-hole-probe.c')))
sdk = Path('/tmp/k148-sdk')
gccdir = next((sdk/'usr/lib/gcc').glob('aarch64-*/*'))
env = dict(os.environ, PATH=str(sdk/'usr/bin')+':'+os.environ['PATH'],
           LD_LIBRARY_PATH=str(sdk/'usr/lib')+':'+str(sdk/'lib'))
command = [str(sdk/'usr/bin/gcc'), '--sysroot='+str(sdk), '-B'+str(gccdir)+'/',
           '-B'+str(sdk/'usr/bin')+'/', '-O2', '-Wall', '-Wextra', str(probe),
           '-L/usr/lib', '-l:libvulkan.so.1', '-o', str(out/'vulkan-hole-probe')]
with (out/'hole-compiler-private.log').open('wb') as log:
    subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
print(json.dumps(dict(compiled=True, source_sha256=hashlib.sha256(probe.read_bytes()).hexdigest(),
                     binary_sha256=hashlib.sha256((out/'vulkan-hole-probe').read_bytes()).hexdigest())))
