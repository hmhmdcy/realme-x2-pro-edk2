"""Use public buffer-removal callbacks and verify the whole stream's PTS span."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel264');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire264-native-stream';assert not W.exists();W.mkdir()
s=(R.parent/'kernel263/native-stream-probe.c').read_text()
s=s.replace('int64_t last_pts;','int64_t last_pts, first_pts; unsigned removed_held;')
s=s.replace('d->last_pts=meta->pts;', 'if(d->frames==1)d->first_pts=meta->pts;\n  d->last_pts=meta->pts;')
needle='if(d->held[i].buffer==buffer){d->held[i].buffer=NULL;d->errors++;}'
assert s.count(needle)==1;s=s.replace(needle,'if(d->held[i].buffer==buffer){release(d,&d->held[i]);d->removed_held++;}')
needle=' printf("{\\"source_factory';start=s.index(needle);end=s.index('\n}',start)
s=s[:start]+''' printf("{\\"source_factory\\":\\"pw_stream\\",\\"buffers\\":%u,\\"held_checked\\":%u,\\"held_content_changed\\":%u,\\"held_bytes_sampled\\":65536,\\"metadata_busy_missing\\":%u,\\"errors_count\\":%u,\\"pts_strictly_increasing\\":%s,\\"pts_span_seconds\\":%.9f,\\"held_validated_on_remove\\":%u,\\"shared_bufferpool\\":true,\\"stopped\\":true}\\n",d.frames,d.checked,d.changed,d.busy_missing,d.errors,d.pts_bad?"false":"true",(d.last_pts-d.first_pts)/1e9,d.removed_held);
 return d.frames>20 && !d.errors && !d.changed && !d.pts_bad && !d.busy_missing && d.last_pts-d.first_pts>10*INT64_C(1000000000)?0:1;'''+s[end:]
(R/'native-stream-probe.c').write_text(s);(W/'probe.c').write_text(s)
q=subprocess.run(['chroot',str(SDK),'gcc','-std=gnu11','-O2','-Wall','-Wextra','-I/work/pipewire262/sdk/usr/include/pipewire-0.3','-I/work/pipewire262/sdk/usr/include/spa-0.2','/work/pipewire264-native-stream/probe.c','/work/pipewire263-broadcast/build/src/pipewire/libpipewire-0.3.so.0.1609.0','-o','/work/pipewire264-native-stream/probe'],capture_output=True)
(P/'native-stream-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')[-2500:]
shutil.copyfile(W/'probe',P/'native-stream-probe')
result=dict(compiled=True,sha256=hashlib.sha256((W/'probe').read_bytes()).hexdigest(),source_sha256=hashlib.sha256(s.encode()).hexdigest(),public_pw_stream_api=True,held_content_and_pts_checked_before_remove=True,minimum_pts_span_seconds=10)
(R/'native-stream-build-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
