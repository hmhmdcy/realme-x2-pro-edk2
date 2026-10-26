"""Observe standard frame-sync events and deliberately exhaust statistics buffers."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel296/samurai-stats-late.c').read_text().replace('k296','k297').replace("'#296 '","'#297 '").replace('"#296 "','"#297 "')
needle='static int params_fd=-1;'
events=r'''
static int event_fd=-1;static unsigned stream_epoch;
static bool hold_statistics;static unsigned held_statistics[3],held_count;
static int drain_sof(unsigned context) {
 for(;;){struct v4l2_event e={0};
  if(ioctl(event_fd,VIDIOC_DQEVENT,&e)){if(errno==EAGAIN)return 0;return -1;}
  if(e.type!=V4L2_EVENT_FRAME_SYNC){errno=EPROTO;return -1;}
  printf("SOF epoch=%u context=%u sequence=%u event_sequence=%u pending=%u timestamp_ns=%" PRId64 "\n",stream_epoch,context,e.u.frame_sync.frame_sequence,e.sequence,e.pending,(int64_t)e.timestamp.tv_sec*1000000000+e.timestamp.tv_nsec);fflush(stdout);
 }
}
'''
assert needle in s;s=s.replace(needle,events+'\n'+needle,1)
needle='if(sensor<0||phy<0||csid<0||vfe<0)goto cleanup;'
assert needle in s
s=s.replace(needle,needle+'''
 event_fd=vfe;int event_flags=fcntl(vfe,F_GETFL);
 if(event_flags<0||fcntl(vfe,F_SETFL,event_flags|O_NONBLOCK)<0)goto cleanup;
 struct v4l2_event_subscription subscription={.type=V4L2_EVENT_FRAME_SYNC};
 if(call(vfe,VIDIOC_SUBSCRIBE_EVENT,&subscription))goto cleanup;
''',1)
needle='for(unsigned frame=0;frame<99;frame++)'
assert needle in s;s=s.replace(needle,'for(unsigned frame=0;frame<126;frame++)',1)
needle='if(call(video,VIDIOC_STREAMOFF,&type))goto cleanup;streaming=false;'
assert needle in s
s=s.replace(needle,'if(drain_sof(frame))goto cleanup;'+needle+'\n    if(drain_sof(frame))goto cleanup;stream_epoch++;',1)
needle='  struct pollfd p={.fd=video,.events=POLLIN};'
assert needle in s
s=s.replace(needle,'''
  if(frame==99){hold_statistics=true;puts("STATS_STARVATION_BEGIN_IMAGE_CONTINUES");}
  if(frame==108){
   if(held_count!=3){errno=EPROTO;goto cleanup;}
   hold_statistics=false;
   for(unsigned n=0;n<held_count;n++)if(stats_queue(held_statistics[n]))goto cleanup;
   puts("STATS_STARVATION_REQUEUE_IMAGE_CONTINUES");
  }
'''+needle,1)
needle=' if(b.index>=stats_buffers||b.flags&V4L2_BUF_FLAG_ERROR||b.bytesused!='
assert needle in s;s=s.replace(needle,' if(b.index>=stats_buffers||b.bytesused!=',1)
needle=' const unsigned char *data=stats_maps[b.index];'
assert needle in s
s=s.replace(needle,'''
 if(b.flags&V4L2_BUF_FLAG_ERROR){
  printf("STATS_ERROR frame=%u phase=%u index=%u sequence=%u flags=%u\\n",frame,frame/9,b.index,b.sequence,b.flags);fflush(stdout);
  if(frame<108||frame>109){errno=EPROTO;return -1;}
  return stats_queue(b.index);
 }
'''+needle,1)
needle=' return stats_queue(b.index);\n}\nstatic int stats_drain_stopped'
assert needle in s
s=s.replace(needle,''' if(hold_statistics){
  if(held_count>=3){errno=EOVERFLOW;return -1;}held_statistics[held_count++]=b.index;return 0;
 }
 return stats_queue(b.index);
}
static int stats_drain_stopped''',1)
needle='if(stats_streaming&&stats_dequeue(frame,argv[2]))goto cleanup;'
assert needle in s
s=s.replace(needle,'if(stats_streaming&&(frame<102||frame>=108)&&stats_dequeue(frame,argv[2]))goto cleanup;',1)
needle='  if(call(video,VIDIOC_QBUF,&buffer))goto cleanup;\n }'
assert needle in s
pos=s.rfind(needle);s=s[:pos]+'  if(drain_sof(frame))goto cleanup;\n'+s[pos:]
(HERE/'samurai-stats.c').write_text(s)
s=(HERE.parent/'kernel296/native-stats.py').read_text().replace('k296','k297').replace('stage=296','stage=297').replace('kernel_build=296','kernel_build=297').replace("'#296 '","'#297 '")
s=s.replace("report['actual_frames']==99","report['actual_frames']==126").replace('len(images)==11','len(images)>=13').replace("report['parameter_completions']==7","report['parameter_completions']==8")
s=s.replace("report['statistics_frames']==90", "report['statistics_frames']+len(re.findall(r'^STATS_ERROR ',text,re.M))==111")
s=s.replace(" report['statistics_frames']=len(report['statistics'])", " report['statistics_frames']=len(report['statistics'])\n report['statistics_error_packets']=len(re.findall(r'^STATS_ERROR ',text,re.M))\n report['sof_events']=len(re.findall(r'^SOF ',text,re.M))")
(HERE/'native-stats.py').write_text(s)
for tag in ['stats','optical']:
 p=HERE/('samurai-'+tag+'.c');binary=host.PRIVATE/(tag+'-aarch64-private')
 q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
 (host.PRIVATE/(tag+'-compile-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
 assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
 assert subprocess.run(['qemu-aarch64',str(binary),'--pattern' if tag=='stats' else '--capture','/tmp/wrong-kernel-k297'],capture_output=True,timeout=10).returncode==3
 proof=dict(stage=297,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,wrong_kernel_guard_pass=True,not_run_on_phone=True)
 (HERE/(tag+'-tool-validation.json')).write_text(json.dumps(proof,indent=2)+'\n')
print('Compiled bounded frame-event/late-ROI/statistics-starvation probe and unchanged optical probe.')
