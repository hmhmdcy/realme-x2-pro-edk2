"""Add a public mapped-region lookup; build without leaving SDK sources modified."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
import host
R=Path(__file__).parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-retained-busy';core=SDK/'work/pipewire263-broadcast';base=core/'pipewire-1.6.9'
out=W/'core-map-lookup';assert not out.exists();out.mkdir()
files={n:(base/'src/pipewire'/n).read_bytes() for n in ['mem.c','mem.h']}
c=files['mem.c'].decode();h=files['mem.h'].decode()
needle='SPA_EXPORT\nstruct pw_memblock * pw_mempool_find_id';assert c.count(needle)==1
function='''/* A block imported from a remote client need not have a default map.
 * Query its live region instead of assuming block->map is populated. */
SPA_EXPORT
struct pw_memmap * pw_mempool_find_map(struct pw_mempool *pool,
        const void *ptr, uint32_t size)
{
    struct mempool *impl = SPA_CONTAINER_OF(pool, struct mempool, this);
    struct memblock *b;
    struct memmap *mm;

    spa_list_for_each(b, &impl->blocks, link) {
        spa_list_for_each(mm, &b->memmaps, link) {
            uintptr_t start = (uintptr_t) mm->this.ptr;
            uintptr_t address = (uintptr_t) ptr;
            if (address >= start && address - start < mm->this.size &&
                    size <= mm->this.size - (address - start))
                return &mm->this;
        }
    }
    errno = EFAULT;
    return NULL;
}

'''
c=c.replace(needle,function+needle)
needle='/** Find memblock for given \\a id */';assert h.count(needle)==1
h=h.replace(needle,'''/** Find a live mapped region containing the complete pointer range.
 * The returned map is borrowed and valid only until that map is freed.
 * Call from the pool owner thread or while its loop is locked. */
struct pw_memmap * pw_mempool_find_map(struct pw_mempool *pool,
        const void *ptr, uint32_t size);

'''+needle)
patch=''
try:
 for n,s in [('mem.c',c),('mem.h',h)]:
  (out/n).write_text(s);(base/'src/pipewire'/n).write_text(s)
  patch+=''.join(difflib.unified_diff(files[n].decode().splitlines(True),s.splitlines(True),fromfile='a/src/pipewire/'+n,tofile='b/src/pipewire/'+n))
 q=subprocess.run(['chroot',str(SDK),'ninja','-C','/work/pipewire263-broadcast/build','-j2','src/pipewire/libpipewire-0.3.so.0.1609.0'],capture_output=True)
 (host.PRIVATE/'mapped-region-core-build-private.log').write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,(q.stdout+q.stderr).decode()[-2500:]
 binary=core/'build/src/pipewire/libpipewire-0.3.so.0.1609.0'
 shutil.copyfile(binary,out/binary.name)
 q=subprocess.run(['chroot',str(SDK),'strip','--strip-unneeded','/work/pipewire265-retained-busy/core-map-lookup/'+binary.name],capture_output=True);assert q.returncode==0
 (out/'libpipewire-0.3.so.0').symlink_to(binary.name)
 shutil.copyfile(out/binary.name,host.PRIVATE/'libpipewire-map-lookup.so')
finally:
 for n,data in files.items():(base/'src/pipewire'/n).write_bytes(data)
assert all((base/'src/pipewire'/n).read_bytes()==data for n,data in files.items())
(R/'core-map-lookup-candidate.patch').write_text(patch)
include=W/'include/pipewire';include.mkdir();shutil.copyfile(out/'mem.h',include/'mem.h')
p=W/'source/gstpipewirepool.c';s=p.read_text();(host.PRIVATE/'gstpool-before-map-lookup-private.c').write_text(s)
s=s.replace('  struct pw_memblock *block;','  struct pw_memblock *block;\n  struct pw_memmap *region;')
s=s.replace('  block = pw_mempool_find_ptr (pool, busy);\n  if (block == NULL || block->map == NULL) {','  region = pw_mempool_find_map (pool, busy, sizeof (*busy));\n  if (region == NULL) {')
s=s.replace('  delta = (uintptr_t) busy - (uintptr_t) block->map->ptr;','  block = region->block;\n  delta = (uintptr_t) busy - (uintptr_t) region->ptr;').replace('block->map->size','region->size').replace('block->map->offset','region->offset');p.write_text(s)
basegst=SDK/'work/pipewire262/pipewire-profile/src/gst';patch=''
for n in ['gstpipewirepool.h','gstpipewirepool.c','gstpipewiresrc.c']:
 patch+=''.join(difflib.unified_diff((basegst/n).read_text().splitlines(True),(W/'source'/n).read_text().splitlines(True),fromfile='a/src/gst/'+n,tofile='b/src/gst/'+n))
(R/'gst-retained-busy-mapped-region-candidate.patch').write_text(patch)
report=dict(stage=265,compiled=True,core_sha256=hashlib.sha256((out/binary.name).read_bytes()).hexdigest(),sdk_core_sources_restored=True,new_api='pw_mempool_find_map',existing_abi_symbols_preserved_check_pending=True,system_not_deployed=True)
(R/'mapped-region-core-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

