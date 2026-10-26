from pathlib import Path
K=Path('/home/cy122/x2pro-linux/libcamera214-root/work/pipewire263-broadcast/pipewire-1.6.9')
for name in ['src/pipewire/stream.c','src/pipewire/impl-port.c','spa/plugins/libcamera/libcamera-source.cpp']:
 p=Path('/home/cy122/x2pro-linux/libcamera214-root/work/pipewire264-reset-output/source/libcamera-source.cpp') if name.startswith('spa/') else K/name
 lines=p.read_text().splitlines();indices=set()
 for i,l in enumerate(lines):
  if any(k in l for k in ['meta_busy','busy->count','tee_process','spa_libcamera_buffer_recycle','pw_stream_dequeue_buffer','pw_stream_queue_buffer','requestComplete(']):indices.update(range(max(0,i-5),min(len(lines),i+13)))
 print('\nFILE '+name)
 for i in sorted(indices):print(str(i+1)+': '+lines[i])
