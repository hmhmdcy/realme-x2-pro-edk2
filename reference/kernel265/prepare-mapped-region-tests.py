"""Prepare a second candidate build and tests using real imported PipeWire maps."""
from pathlib import Path
R=Path(__file__).parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-retained-busy'
s=(R/'build-retained-busy.py').read_text().replace("build=W/'build'","build=W/'build-v2'").replace('/pipewire265-retained-busy/build','/pipewire265-retained-busy/build-v2').replace('-L/work/pipewire262/sdk/usr/lib','-L/work/pipewire265-retained-busy/core-map-lookup').replace('libgstpipewire-retained-busy.so','libgstpipewire-retained-busy-v2.so').replace('retained-busy-build-validation.json','retained-busy-v2-build-validation.json')
(R/'build-retained-busy-v2.py').write_text(s)
out=W/'core-map-lookup';link=out/'libpipewire-0.3.so'
if not link.exists():link.symlink_to('libpipewire-0.3.so.0.1609.0')
s=(R/'test-retained-busy.py').read_text().replace("unit=W/'unit'","unit=W/'unit-v2'").replace('/unit/','/unit-v2/').replace('retained-busy-unit-validation.json','retained-busy-v2-unit-validation.json').replace('retained-busy-test.c','retained-busy-v2-test.c')
a=s.index('static struct pw_memblock fake_block;');b=s.index("'''\nmain=",a)
s=s[:a]+'''static struct pw_mempool *active_pool;
struct pw_core *pw_stream_get_core(struct pw_stream *stream)
{ (void)stream; return (struct pw_core *)active_pool; }
struct pw_mempool *pw_core_get_mempool(struct pw_core *core)
{ assert(core==(struct pw_core *)active_pool); return active_pool; }
'''+s[b:]
s=s.replace('  GstPipeWirePoolData *data;','  GstPipeWirePoolData *data;\n  struct pw_mempool *pool;\n  struct pw_memmap *map;')
a=s.index('  f->old_map=mmap(');b=s.index('  f->meta=',a)
s=s[:a]+'''  f->pool=pw_mempool_new(NULL);assert(f->pool);active_pool=f->pool;
  int imported_fd=fcntl(f->fd,F_DUPFD_CLOEXEC,0);assert(imported_fd>=0);
  struct pw_memblock *block=pw_mempool_import(f->pool,PW_MEMBLOCK_FLAG_READWRITE,SPA_DATA_MemFd,imported_fd);
  assert(block && !block->map);
  f->map=pw_memblock_map(block,PW_MEMMAP_FLAG_READWRITE,f->page,f->page,NULL);assert(f->map);
  f->old_map=f->map->ptr;
  f->observer=mmap(NULL,f->page,PROT_READ|PROT_WRITE,MAP_SHARED,f->fd,f->page);assert(f->observer!=MAP_FAILED);
  void *expected_busy=(char*)f->old_map+128;
  f->count=(struct spa_meta_busy *)((char*)f->observer+128);f->count->count=1;
  assert(pw_mempool_find_map(f->pool,expected_busy,sizeof(*f->count))==f->map);
  assert(!pw_mempool_find_map(f->pool,(char*)f->old_map-1,4));
  assert(!pw_mempool_find_map(f->pool,(char*)f->old_map+f->page,4));
  assert(!pw_mempool_find_map(f->pool,expected_busy,UINT32_MAX));
'''+s[b:]
s=s.replace('  if(f->old_map){assert(munmap(f->old_map,f->page)==0);f->old_map=NULL;}','  if(f->pool){pw_mempool_destroy(f->pool);f->pool=NULL;f->old_map=NULL;}')
s=s.replace('f.data->gst_busy!=(struct spa_meta_busy*)expected_busy','f.data->gst_busy!=(struct spa_meta_busy*)((char*)f.old_map+128)')
s=s.replace('  assert(munmap(f.old_map,f.page)==0);f.old_map=NULL;assert(close(f.fd)==0);f.fd=-1;','  pw_mempool_destroy(f.pool);f.pool=NULL;f.old_map=NULL;assert(close(f.fd)==0);f.fd=-1;')
a=s.index('  missing_block=1;');b=s.index('  assert(!f.data->busy_map',a)
s=s[:a]+'''  void *saved=f.meta.data;f.meta.data=(char*)f.old_map-1;
  assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f) && errno==EFAULT);f.meta.data=saved;
  f.meta.data=(char*)f.old_map+f.page-1;
  assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f) && errno==EFAULT);f.meta.data=saved;
  int saved_fd=f.map->block->fd;f.map->block->fd=-1;
  assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f));f.map->block->fd=saved_fd;
  char path[]="/tmp/k265-busy-readonly-XXXXXX";int tmp=mkstemp(path);assert(tmp>=0);assert(ftruncate(tmp,2*f.page)==0);
  int ro=open(path,O_RDONLY|O_CLOEXEC);assert(ro>=0);assert(unlink(path)==0);close(tmp);
  f.map->block->fd=ro;assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f));close(ro);f.map->block->fd=saved_fd;
'''+s[b:]
s=s.replace('five_mapping_failures_handled','four_mapping_failures_handled')
s=s.replace("'/work/pipewire265-retained-busy/unit-v2/test.c',*flags,","'/work/pipewire265-retained-busy/unit-v2/test.c','-L/work/pipewire265-retained-busy/core-map-lookup','-lpipewire-0.3',*flags,")
s=s.replace("q=inside(['/work/pipewire265-retained-busy/unit-v2/test']","q=inside(['env','LD_LIBRARY_PATH=/work/pipewire265-retained-busy/core-map-lookup','/work/pipewire265-retained-busy/unit-v2/test']")
s=s.replace("q2=inside(['/work/pipewire265-retained-busy/unit-v2/negative']","q2=inside(['env','LD_LIBRARY_PATH=/work/pipewire265-retained-busy/core-map-lookup','/work/pipewire265-retained-busy/unit-v2/negative']")
s=s.replace("arm64_runtime=True,positive=","arm64_runtime=True,real_pipewire_imported_map_without_default_map=True,positive=")
s=s.replace("'retained-unit-","'retained-v2-unit-")
(R/'test-retained-busy-v2.py').write_text(s)
print('Prepared candidate v2 build and real imported-map fixture')

