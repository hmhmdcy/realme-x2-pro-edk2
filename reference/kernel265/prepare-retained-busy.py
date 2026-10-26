"""Keep Gst shared frame ownership alive across PipeWire buffer retirement."""
from pathlib import Path
import difflib,hashlib,json,shutil
import host
R=Path(__file__).parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-retained-busy';assert not W.exists();W.mkdir()
base=SDK/'work/pipewire262/pipewire-profile/src/gst';source=W/'source';shutil.copytree(base,source)
for name in ['gstpipewirepool.c','gstpipewirepool.h','gstpipewiresrc.c']:(host.PRIVATE/(name+'-before-retained-busy-private')).write_bytes((base/name).read_bytes())
p=source/'gstpipewirepool.h';s=p.read_text();needle='  struct spa_meta_cursor *cursor;';assert s.count(needle)==1
s=s.replace(needle,needle+'''
  /* Independent metadata mapping; retired PipeWire maps may disappear while
   * an application still holds a shared GstBuffer. No pixel memory is copied. */
  struct spa_meta_busy *gst_busy;
  void *busy_map;
  gsize busy_map_size;
  gboolean busy_held;''')
needle='GstPipeWirePoolData *gst_pipewire_pool_get_data (GstBuffer *buffer);';assert s.count(needle)==1
s=s.replace(needle,needle+'''

gboolean gst_pipewire_pool_init_busy (GstPipeWirePoolData *data, struct pw_stream *stream);
void gst_pipewire_pool_hold_busy (GstPipeWirePoolData *data);
void gst_pipewire_pool_release_busy (GstPipeWirePoolData *data);
''');p.write_text(s)
p=source/'gstpipewirepool.c';s=p.read_text().replace('#include <unistd.h>','#include <unistd.h>\n#include <fcntl.h>\n#include <sys/mman.h>\n#include <pipewire/mem.h>\n#include <spa/utils/atomic.h>')
start=s.index('static void\npool_data_destroy (');helpers='''/* Gst owns a separate Busy reference for the lifetime of shared frames. The
 * ordinary pw_stream reference may be returned during remove_buffer, before
 * downstream finishes with those frames. Keep the counter mapping independent
 * of pw_stream so that its final decrement remains valid after retirement. */
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

'''
s=s[:start]+helpers+s[start:]
needle='  gst_object_unref (data->pool);';assert s.count(needle)==1
s=s.replace(needle,'''  gst_pipewire_pool_release_busy (data);
  if (data->busy_map != NULL)
    munmap (data->busy_map, data->busy_map_size);
'''+needle);p.write_text(s)
p=source/'gstpipewiresrc.c';s=p.read_text();needle='  pw_thread_loop_unlock (src->stream->core->loop);\n\n  GST_OBJECT_UNLOCK (data->pool);\n\n  return FALSE;';assert s.count(needle)==1
s=s.replace(needle,'''  gst_pipewire_pool_release_busy (data);

'''+needle)
needle='  pwsrc->n_buffers++;\n}';assert s.count(needle)==1
s=s.replace(needle,'''  pwsrc->n_buffers++;
  if (!gst_pipewire_pool_init_busy (data, pwsrc->stream->pwstream)) {
    pw_stream_set_error (pwsrc->stream->pwstream, -errno,
        "cannot retain shared buffer ownership metadata");
  }
}''')
needle='  GstBuffer *buf = data->buf;\n  gboolean flush_on_remove;';assert s.count(needle)==1
s=s.replace(needle,'''  /* Pin across flush-start: downstream may synchronously drop its last ref. */
  GstBuffer *buf = gst_buffer_ref (data->buf);
  gboolean flush_on_remove;''')
start=s.index('static void\non_remove_buffer (');end=s.index('\nstatic const char * const transform_map',start)
block=s[start:end];last=block.rfind('\n}');assert last>0
block=block[:last]+'''\n  /* Retired frames release their own Busy loan when the last Gst ref dies. */
  gst_buffer_unref (buf);'''+block[last:];s=s[:start]+block+s[end:]
needle='    gst_buffer_add_parent_buffer_meta (buf, data->buf);';assert s.count(needle)==1
s=s.replace(needle,'''    gst_pipewire_pool_hold_busy (data);
'''+needle);p.write_text(s)
patch=''
for name in ['gstpipewirepool.h','gstpipewirepool.c','gstpipewiresrc.c']:
 patch+=''.join(difflib.unified_diff((base/name).read_text().splitlines(True),(source/name).read_text().splitlines(True),fromfile='a/src/gst/'+name,tofile='b/src/gst/'+name))
(R/'gst-retained-busy-candidate.patch').write_text(patch)
report=dict(stage=265,source_sha256={n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in ['gstpipewirepool.h','gstpipewirepool.c','gstpipewiresrc.c']},extra_busy_reference_owned_until_gst_frame_release=True,metadata_mapping_independent_of_retired_pw_stream=True,pixel_copy_added=False,system_not_modified=True)
(R/'retained-busy-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

