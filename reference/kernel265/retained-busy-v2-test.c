// SPDX-License-Identifier: MIT
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
gboolean
gst_pipewire_pool_init_busy (GstPipeWirePoolData *data, struct pw_stream *stream)
{
  struct spa_meta_busy *busy = spa_buffer_find_meta_data (data->b->buffer,
      SPA_META_Busy, sizeof (*busy));
  struct pw_memblock *block;
  struct pw_memmap *region;
  struct pw_mempool *pool;
  struct pw_map_range range;
  uintptr_t delta;
  uint64_t offset;
  long page_size;
  void *mapped;
  int fd, saved_errno;

  if (busy == NULL)
    return TRUE;
  pool = pw_core_get_mempool (pw_stream_get_core (stream));
  region = pw_mempool_find_map (pool, busy, sizeof (*busy));
  if (region == NULL) {
    errno = EFAULT;
    return FALSE;
  }
  block = region->block;
  delta = (uintptr_t) busy - (uintptr_t) region->ptr;
  if (delta > region->size || sizeof (*busy) > region->size - delta) {
    errno = EFAULT;
    return FALSE;
  }
  offset = (uint64_t) region->offset + delta;
  page_size = sysconf (_SC_PAGESIZE);
  if (offset > UINT32_MAX || page_size <= 0 || page_size > UINT32_MAX ||
      pw_map_range_init (&range, offset, sizeof (*busy), page_size) < 0) {
    errno = EOVERFLOW;
    return FALSE;
  }
  fd = fcntl (block->fd, F_DUPFD_CLOEXEC, 0);
  if (fd < 0)
    return FALSE;
  mapped = mmap (NULL, range.size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, range.offset);
  saved_errno = errno;
  close (fd);
  if (mapped == MAP_FAILED) {
    errno = saved_errno;
    return FALSE;
  }
  data->busy_map = mapped;
  data->busy_map_size = range.size;
  data->gst_busy = SPA_PTROFF (mapped, range.start, struct spa_meta_busy);
  return TRUE;
}

void
gst_pipewire_pool_hold_busy (GstPipeWirePoolData *data)
{
  if (data->gst_busy != NULL && !data->busy_held) {
    SPA_ATOMIC_INC (data->gst_busy->count);
    data->busy_held = TRUE;
  }
}

void
gst_pipewire_pool_release_busy (GstPipeWirePoolData *data)
{
  if (data->busy_held) {
    SPA_ATOMIC_DEC (data->gst_busy->count);
    data->busy_held = FALSE;
  }
}

static void
pool_data_destroy (gpointer user_data)
{
  GstPipeWirePoolData *data = user_data;

  gst_pipewire_pool_release_busy (data);
  if (data->busy_map != NULL)
    munmap (data->busy_map, data->busy_map_size);
  gst_object_unref (data->pool);
  g_free (data);
}

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
