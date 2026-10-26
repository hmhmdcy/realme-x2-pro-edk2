"""Exercise the actual Gst Busy helpers with shared memfds and real Gst parent refs."""
from pathlib import Path
import hashlib,json,os,resource,shlex,subprocess
import host
R=Path(__file__).parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-retained-busy';p=W/'source/gstpipewirepool.c';text=p.read_text()
helpers=text[text.index('gboolean\ngst_pipewire_pool_init_busy'):text.index('\nvoid gst_pipewire_pool_wrap_buffer')]
prefix=r'''// SPDX-License-Identifier: MIT
// Actual candidate helper functions are inserted below, without rewriting them.
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <dirent.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "gstpipewirepool.h"
#include <pipewire/mem.h>
#include <spa/utils/atomic.h>

static struct pw_mempool *active_pool;
struct pw_core *pw_stream_get_core(struct pw_stream *stream)
{ (void)stream; return (struct pw_core *)active_pool; }
struct pw_mempool *pw_core_get_mempool(struct pw_core *core)
{ assert(core==(struct pw_core *)active_pool); return active_pool; }
'''
main=r'''
static int fd_count(void)
{
  int n=0;
  for(int fd=0;fd<1024;fd++)if(fcntl(fd,F_GETFD)>=0)n++;
  return n;
}
struct fixture {
  int fd;
  long page;
  void *old_map,*observer;
  struct spa_meta meta;
  struct spa_buffer spa;
  struct pw_buffer pw;
  GstPipeWirePoolData *data;
  struct pw_mempool *pool;
  struct pw_memmap *map;
  struct spa_meta_busy *count;
};
static void fixture_open(struct fixture *f)
{
  memset(f,0,sizeof(*f));f->page=sysconf(_SC_PAGESIZE);assert(f->page>0);
  f->fd=memfd_create("busy-reference-test",MFD_CLOEXEC);assert(f->fd>=0 && f->fd<1024);
  assert(ftruncate(f->fd,2*f->page)==0);
  f->pool=pw_mempool_new(NULL);assert(f->pool);active_pool=f->pool;
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
  f->meta=(struct spa_meta){.type=SPA_META_Busy,.size=sizeof(struct spa_meta_busy),.data=expected_busy};
  f->spa=(struct spa_buffer){.n_metas=1,.metas=&f->meta};f->pw=(struct pw_buffer){.buffer=&f->spa};
  f->data=g_new0(GstPipeWirePoolData,1);f->data->pool=(GstPipeWirePool*)gst_buffer_pool_new();f->data->b=&f->pw;
}
static void fixture_close(struct fixture *f)
{
  if(f->pool){pw_mempool_destroy(f->pool);f->pool=NULL;f->old_map=NULL;}
  if(f->fd>=0){assert(close(f->fd)==0);f->fd=-1;}
  assert(munmap(f->observer,f->page)==0);
}
static void normal_release(void)
{
  struct fixture f;fixture_open(&f);
  assert(gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f));
  assert(f.data->busy_map && f.data->gst_busy!=(struct spa_meta_busy*)((char*)f.old_map+128));
  gst_pipewire_pool_hold_busy(f.data);assert(f.count->count==2);
  gst_pipewire_pool_hold_busy(f.data);assert(f.count->count==2);
  gst_pipewire_pool_release_busy(f.data);assert(f.count->count==1);
  gst_pipewire_pool_release_busy(f.data);assert(f.count->count==1);
  SPA_ATOMIC_DEC(f.count->count);assert(f.count->count==0);
  pool_data_destroy(f.data);assert(f.count->count==0);fixture_close(&f);
}
static void retained_after_retirement(void)
{
  struct fixture f;fixture_open(&f);
  assert(gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f));
  GstBuffer *parent=gst_buffer_new_allocate(NULL,128,NULL);
  gst_mini_object_set_qdata(GST_MINI_OBJECT_CAST(parent),g_quark_from_static_string("actual-busy-test"),f.data,pool_data_destroy);
  f.data->buf=parent;
  gst_pipewire_pool_hold_busy(f.data);assert(f.count->count==2);
  GstBuffer *frame=gst_buffer_new_allocate(NULL,128,NULL);
  assert(gst_buffer_add_parent_buffer_meta(frame,parent));gst_buffer_unref(parent);
  GstBuffer *retained=gst_buffer_copy(frame);assert(retained);gst_buffer_unref(frame);
  /* remove_buffer pins the parent, queues the PW loan and drops its pin. */
  gst_buffer_ref(parent);SPA_ATOMIC_DEC(f.count->count);gst_buffer_unref(parent);
  assert(f.count->count==1);
  pw_mempool_destroy(f.pool);f.pool=NULL;f.old_map=NULL;assert(close(f.fd)==0);f.fd=-1;
  assert(f.count->count==1);
  /* The last application Gst ref dies after the original PW mapping is gone. */
  gst_buffer_unref(retained);assert(f.count->count==0);fixture_close(&f);
}
static void absent_meta(void)
{
  struct fixture f;fixture_open(&f);f.spa.n_metas=0;
  assert(gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f));assert(!f.data->busy_map);
  gst_pipewire_pool_hold_busy(f.data);gst_pipewire_pool_release_busy(f.data);assert(f.count->count==1);
  pool_data_destroy(f.data);fixture_close(&f);
}
static void failures(void)
{
  struct fixture f;fixture_open(&f);
  void *saved=f.meta.data;f.meta.data=(char*)f.old_map-1;
  assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f) && errno==EFAULT);f.meta.data=saved;
  f.meta.data=(char*)f.old_map+f.page-1;
  assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f) && errno==EFAULT);f.meta.data=saved;
  int saved_fd=f.map->block->fd;f.map->block->fd=-1;
  assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f));f.map->block->fd=saved_fd;
  char path[]="/tmp/k265-busy-readonly-XXXXXX";int tmp=mkstemp(path);assert(tmp>=0);assert(ftruncate(tmp,2*f.page)==0);
  int ro=open(path,O_RDONLY|O_CLOEXEC);assert(ro>=0);assert(unlink(path)==0);close(tmp);
  f.map->block->fd=ro;assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f));close(ro);f.map->block->fd=saved_fd;
  assert(!f.data->busy_map && !f.data->busy_held && f.count->count==1);
  pool_data_destroy(f.data);fixture_close(&f);
}
int main(void)
{
  gst_init(NULL,NULL);GstBufferPool *prime=gst_buffer_pool_new();gst_object_unref(prime);
  normal_release();retained_after_retirement();absent_meta();failures();
  int before=fd_count();
  for(int i=0;i<64;i++){normal_release();retained_after_retirement();absent_meta();failures();}
  assert(fd_count()==before);
  puts("{\"cases\":260,\"normal_release\":true,\"retired_mapping_with_live_parent_copy\":true,\"absent_meta_unchanged\":true,\"four_mapping_failures_handled\":true,\"fd_growth\":0}");
  return 0;
}
'''
source=prefix+helpers+main;(R/'retained-busy-v2-test.c').write_text(source);unit=W/'unit-v2';unit.mkdir(exist_ok=True);(unit/'test.c').write_text(source)
packages=['gstreamer-1.0','gstreamer-video-1.0','gstreamer-audio-1.0']
def inside(args,**kwargs):return subprocess.run(['chroot',str(SDK),*args],capture_output=True,**kwargs)
flags=shlex.split(inside(['pkg-config','--cflags','--libs',*packages]).stdout.decode())
args=['cc','-O1','-g','-Wall','-Wextra','-Werror','-I/work/pipewire265-retained-busy/build','-I/work/pipewire265-retained-busy/source','-I/work/pipewire265-retained-busy/include','-I/work/pipewire262/sdk/usr/include/pipewire-0.3','-I/work/pipewire262/sdk/usr/include/spa-0.2','/work/pipewire265-retained-busy/unit-v2/test.c','-L/work/pipewire265-retained-busy/core-map-lookup','-lpipewire-0.3',*flags,'-o','/work/pipewire265-retained-busy/unit-v2/test']
q=inside(args);(host.PRIVATE/'retained-v2-unit-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()[-2800:]
def limit():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
env=os.environ.copy();env.update(GST_PLUGIN_SYSTEM_PATH='',GST_PLUGIN_PATH='',GST_REGISTRY='/tmp/k265-busy-unit-registry.bin')
q=inside(['env','LD_LIBRARY_PATH=/work/pipewire265-retained-busy/core-map-lookup','/work/pipewire265-retained-busy/unit-v2/test'],env=env,preexec_fn=limit,timeout=20);(host.PRIVATE/'retained-v2-unit-runtime-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()[-2800:]
negative=helpers.replace('    SPA_ATOMIC_INC (data->gst_busy->count);','    /* Negative control: deliberately remove the Gst ownership increment. */',1);assert negative!=helpers
(unit/'negative.c').write_text(prefix+negative+main);nargs=[x.replace('/unit-v2/test.c','/unit-v2/negative.c').replace('/unit-v2/test','/unit-v2/negative') for x in args]
q2=inside(nargs);assert q2.returncode==0,q2.stderr.decode()[-1800:]
q2=inside(['env','LD_LIBRARY_PATH=/work/pipewire265-retained-busy/core-map-lookup','/work/pipewire265-retained-busy/unit-v2/negative'],env=env,preexec_fn=limit,timeout=20);(host.PRIVATE/'retained-v2-unit-negative-private.log').write_bytes(q2.stdout+q2.stderr);assert q2.returncode!=0
report=dict(stage=265,actual_candidate_helpers_sha256=hashlib.sha256(helpers.encode()).hexdigest(),arm64_runtime=True,real_pipewire_imported_map_without_default_map=True,positive=json.loads(q.stdout),missing_ownership_increment_negative_control_rejected=True,negative_exit=q2.returncode,system_not_modified=True)
(R/'retained-busy-v2-unit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

