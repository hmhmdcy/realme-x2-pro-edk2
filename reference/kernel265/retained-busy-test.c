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

static struct pw_memblock fake_block;
static struct pw_memmap fake_map;
static struct pw_mempool fake_pool;
static void *expected_busy;
static int missing_block;
struct pw_core *pw_stream_get_core(struct pw_stream *stream)
{ (void)stream; return (struct pw_core *)&fake_pool; }
struct pw_mempool *pw_core_get_mempool(struct pw_core *core)
{ assert(core==(struct pw_core *)&fake_pool); return &fake_pool; }
struct pw_memblock *pw_mempool_find_ptr(struct pw_mempool *pool,const void *ptr)
{ assert(pool==&fake_pool && ptr==expected_busy); return missing_block ? NULL : &fake_block; }
gboolean
gst_pipewire_pool_init_busy (GstPipeWirePoolData *data, struct pw_stream *stream)
{
  struct spa_meta_busy *busy = spa_buffer_find_meta_data (data->b->buffer,
      SPA_META_Busy, sizeof (*busy));
  struct pw_memblock *block;
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
  block = pw_mempool_find_ptr (pool, busy);
  if (block == NULL || block->map == NULL) {
    errno = EFAULT;
    return FALSE;
  }
  delta = (uintptr_t) busy - (uintptr_t) block->map->ptr;
  if (delta > block->map->size || sizeof (*busy) > block->map->size - delta) {
    errno = EFAULT;
    return FALSE;
  }
  offset = (uint64_t) block->map->offset + delta;
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
  struct spa_meta_busy *count;
};
static void fixture_open(struct fixture *f)
{
  memset(f,0,sizeof(*f));f->page=sysconf(_SC_PAGESIZE);assert(f->page>0);
  f->fd=memfd_create("busy-reference-test",MFD_CLOEXEC);assert(f->fd>=0 && f->fd<1024);
  assert(ftruncate(f->fd,2*f->page)==0);
  f->old_map=mmap(NULL,f->page,PROT_READ|PROT_WRITE,MAP_SHARED,f->fd,f->page);
  f->observer=mmap(NULL,f->page,PROT_READ|PROT_WRITE,MAP_SHARED,f->fd,f->page);
  assert(f->old_map!=MAP_FAILED && f->observer!=MAP_FAILED);
  expected_busy=(char*)f->old_map+128;f->count=(struct spa_meta_busy *)((char*)f->observer+128);f->count->count=1;
  fake_map=(struct pw_memmap){.ptr=f->old_map,.offset=f->page,.size=f->page};
  fake_block=(struct pw_memblock){.pool=&fake_pool,.fd=f->fd,.map=&fake_map,.size=2*f->page};
  missing_block=0;
  f->meta=(struct spa_meta){.type=SPA_META_Busy,.size=sizeof(struct spa_meta_busy),.data=expected_busy};
  f->spa=(struct spa_buffer){.n_metas=1,.metas=&f->meta};f->pw=(struct pw_buffer){.buffer=&f->spa};
  f->data=g_new0(GstPipeWirePoolData,1);f->data->pool=(GstPipeWirePool*)gst_buffer_pool_new();f->data->b=&f->pw;
}
static void fixture_close(struct fixture *f)
{
  if(f->old_map){assert(munmap(f->old_map,f->page)==0);f->old_map=NULL;}
  if(f->fd>=0){assert(close(f->fd)==0);f->fd=-1;}
  assert(munmap(f->observer,f->page)==0);
}
static void normal_release(void)
{
  struct fixture f;fixture_open(&f);
  assert(gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f));
  assert(f.data->busy_map && f.data->gst_busy!=(struct spa_meta_busy*)expected_busy);
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
  assert(munmap(f.old_map,f.page)==0);f.old_map=NULL;assert(close(f.fd)==0);f.fd=-1;
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
  missing_block=1;assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f) && errno==EFAULT);missing_block=0;
  fake_block.map=NULL;assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f) && errno==EFAULT);fake_block.map=&fake_map;
  fake_map.size=128;assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f) && errno==EFAULT);fake_map.size=f.page;
  fake_block.fd=-1;assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f));fake_block.fd=f.fd;
  char path[]="/tmp/k265-busy-readonly-XXXXXX";int tmp=mkstemp(path);assert(tmp>=0);assert(ftruncate(tmp,2*f.page)==0);
  int ro=open(path,O_RDONLY|O_CLOEXEC);assert(ro>=0);assert(unlink(path)==0);close(tmp);
  fake_block.fd=ro;assert(!gst_pipewire_pool_init_busy(f.data,(struct pw_stream*)&f));close(ro);fake_block.fd=f.fd;
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
  puts("{\"cases\":260,\"normal_release\":true,\"retired_mapping_with_live_parent_copy\":true,\"absent_meta_unchanged\":true,\"five_mapping_failures_handled\":true,\"fd_growth\":0}");
  return 0;
}
