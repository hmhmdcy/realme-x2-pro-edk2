"""Retain R1 and handle the actual V4L2 empty-event return in an independent R2."""
from pathlib import Path
import hashlib,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'stats-capture-validation.json').read_text())['tool_exit']==1
s=(HERE/'samurai-stats.c').read_text()
needle='if(errno==EAGAIN)return 0;'
assert needle in s
s=s.replace(needle,'if(errno==EAGAIN||errno==ENOENT)return 0;',1)
p=HERE/'samurai-stats-r2.c';assert not p.exists();p.write_text(s)
binary=host.PRIVATE/'stats-r2-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'stats-r2-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/wrong-kernel-k297'],capture_output=True,timeout=10).returncode==3
(HERE/'stats-r2-tool-validation.json').write_text(json.dumps(dict(stage=297,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,wrong_kernel_guard_pass=True,not_run_on_phone=True,empty_event_enoent_supported=True),indent=2)+'\n')
for old,new in [('native-stats.py','native-stats-r2.py'),('launch-stats.py','launch-stats-r2.py'),('poll-stats.py','poll-stats-r2.py')]:
 t=(HERE/old).read_text().replace('k297-stats-r1','k297-stats-r2').replace('k297-tools/stats','k297-tools/stats-r2').replace('native-stats.py','native-stats-r2.py')
 t=t.replace('stats-aarch64-private','stats-r2-aarch64-private').replace('stats-tool-validation.json','stats-r2-tool-validation.json').replace('stats-launch-private.json','stats-r2-launch-private.json').replace('stats-poll-private.json','stats-r2-poll-private.json').replace('stats-capture-validation.json','stats-r2-capture-validation.json').replace('stats-worker-private.log','stats-r2-worker-private.log')
 p=HERE/new;assert not p.exists();compile(t,str(p),'exec');p.write_text(t)
for name in ['analyze-sof.py','analyze-frame-association.py']:
 p=HERE/name;t=p.read_text().replace('stats-capture-validation.json','stats-r2-capture-validation.json');p.write_text(t)
p=HERE/'analyze-stats-color.py';p.write_text(p.read_text().replace('k297-stats-r1','k297-stats-r2'))
routine=re.search(r'static int drain_sof\(.*?\n\}',s,re.S)[0]
harness=r'''
#include <assert.h>
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#define V4L2_EVENT_FRAME_SYNC 1
#define VIDIOC_DQEVENT 2
struct v4l2_event {unsigned type,sequence,pending;struct timespec timestamp;union {struct {unsigned frame_sequence;} frame_sync;}u;};
static int event_fd;static unsigned stream_epoch,remain;static int end_error;
static int fake_ioctl(int fd,unsigned cmd,struct v4l2_event *e) {(void)fd;(void)cmd;if(!remain){errno=end_error;return -1;}remain--;e->type=V4L2_EVENT_FRAME_SYNC;return 0;}
#define ioctl fake_ioctl
'''+routine+r'''
int main(void){end_error=ENOENT;assert(!drain_sof(0));end_error=EAGAIN;assert(!drain_sof(0));remain=2;assert(!drain_sof(1));end_error=EINVAL;assert(drain_sof(2)==-1);}
'''
p=host.PRIVATE/'event-drain-host-private.c';p.write_text(harness)
b=host.PRIVATE/'event-drain-host-private'
subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p),'-o',str(b)],check=True)
subprocess.run([str(b)],check=True,capture_output=True)
(HERE/'event-drain-validation.json').write_text(json.dumps(dict(stage=297,enoent_and_eagain_supported=True,events_drained=True,other_errors_preserved=True,asan_ubsan=True,failed_first_probe_preserved=True),indent=2)+'\n')
print('R1 preserved; compiled and tested independent R2 event drain; no kernel change.')
