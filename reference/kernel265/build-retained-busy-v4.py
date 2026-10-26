"""Add ownership diagnostics to the v3 src object; keep tested Busy helper bytes identical."""
from pathlib import Path
import hashlib,json,shlex,shutil,subprocess
import host
R=Path(__file__).parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-retained-busy';V=W/'v4';assert not V.exists();V.mkdir();source=V/'source';shutil.copytree(W/'v3/source',source)
p=source/'gstpipewiresrc.c';s=p.read_text()
s='#include <sys/stat.h>\n#include <pipewire/mem.h>\n#include <spa/utils/atomic.h>\n'+s
needle='  pwsrc->n_buffers++;\n';assert s.count(needle)==1
s=s.replace(needle,needle) # Initialization remains before the diagnostic.
needle='''        "cannot retain shared buffer ownership metadata");
  }
}''';assert s.count(needle)==1
s=s.replace(needle,'''        "cannot retain shared buffer ownership metadata");
  }
  struct spa_meta_busy *busy = spa_buffer_find_meta_data (b->buffer,
      SPA_META_Busy, sizeof (struct spa_meta_busy));
  struct pw_memmap *map = busy ? pw_mempool_find_map (
      pw_core_get_mempool (pw_stream_get_core (pwsrc->stream->pwstream)),
      busy, sizeof (*busy)) : NULL;
  struct stat metadata_stat = { 0 }, image_stat = { 0 };
  if (map) fstat (map->block->fd, &metadata_stat);
  if (b->buffer->n_datas && b->buffer->datas[0].fd >= 0)
    fstat (b->buffer->datas[0].fd, &image_stat);
  GST_INFO_OBJECT (pwsrc, "ownership-add buffer:%p busy:%p count:%u meta-inode:%llu image-inode:%llu type:%u",
      data->buf, data->gst_busy, data->gst_busy ? SPA_ATOMIC_LOAD (data->gst_busy->count) : 0,
      (unsigned long long) metadata_stat.st_ino, (unsigned long long) image_stat.st_ino,
      b->buffer->n_datas ? b->buffer->datas[0].type : 0);
}''')
needle='    gst_pipewire_pool_hold_busy (data);';assert s.count(needle)==1
s=s.replace(needle,needle+'''
    GST_LOG_OBJECT (pwsrc, "ownership-held buffer:%p seq:%u pts:%" G_GUINT64_FORMAT " busy:%p count:%u held:%d",
        data->buf, h ? h->seq : 0, h ? h->pts : 0, data->gst_busy,
        data->gst_busy ? SPA_ATOMIC_LOAD (data->gst_busy->count) : 0, data->busy_held);''')
needle='''      buf, data->queued);

  GST_MINI_OBJECT_CAST (buf)->dispose = NULL;''';assert s.count(needle)==1
s=s.replace(needle,'''      buf, data->queued);
  GST_INFO_OBJECT (pwsrc, "ownership-remove buffer:%p busy:%p count:%u held:%d",
      buf, data->gst_busy, data->gst_busy ? SPA_ATOMIC_LOAD (data->gst_busy->count) : 0,
      data->busy_held);

  GST_MINI_OBJECT_CAST (buf)->dispose = NULL;''');p.write_text(s)
def inside(args):return subprocess.run(['chroot',str(SDK),*args],capture_output=True)
pkgs=['gstreamer-1.0','gstreamer-base-1.0','gstreamer-video-1.0','gstreamer-audio-1.0','gstreamer-net-1.0','gstreamer-allocators-1.0'];flags=shlex.split(inside(['pkg-config','--cflags',*pkgs]).stdout.decode());libs=shlex.split(inside(['pkg-config','--libs',*pkgs]).stdout.decode())
common=['cc','-fPIC','-O2','-Wall','-Wextra','-Wno-unused-parameter','-I/work/pipewire265-retained-busy/build-v2','-I/work/pipewire265-retained-busy/v4/source','-I/work/pipewire265-retained-busy/include','-I/work/pipewire262/sdk/usr/include/pipewire-0.3','-I/work/pipewire262/sdk/usr/include/spa-0.2',*flags]
q=inside([*common,'-c','/work/pipewire265-retained-busy/v4/source/gstpipewiresrc.c','-o','/work/pipewire265-retained-busy/v4/gstpipewiresrc.o']);(host.PRIVATE/'v4-ownership-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()[-2500:]
objects=['/'+str(p.relative_to(SDK)) for p in sorted((W/'build-v2').glob('*.o')) if p.name!='gstpipewiresrc.o']+['/work/pipewire265-retained-busy/v4/gstpipewiresrc.o']
q=inside(['cc','-shared',*objects,'-L/work/pipewire265-retained-busy/core-map-lookup','-lpipewire-0.3','-lm',*libs,'-o','/work/pipewire265-retained-busy/v4/libgstpipewire.so']);assert q.returncode==0,q.stderr.decode();assert inside(['strip','--strip-unneeded','/work/pipewire265-retained-busy/v4/libgstpipewire.so']).returncode==0
binary=V/'libgstpipewire.so';shutil.copyfile(binary,host.PRIVATE/'libgstpipewire-retained-busy-v4.so')
report=dict(stage=265,compiled=True,plugin_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(s.encode()).hexdigest(),busy_helpers_unchanged=True,diagnostic_additions_only_relative_to_v3=True,system_not_deployed=True)
(R/'retained-busy-v4-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

