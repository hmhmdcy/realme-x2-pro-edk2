"""Offline F2FS used-block image, compressed stream, bounded RAM tail recovery."""
from pathlib import Path
import hashlib,hmac,http.server,json,os,re,socketserver,subprocess,sys,time,traceback
os.umask(0o077);cfg=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else '/run/k248-userdata-config-private.json').read_text());o=Path(cfg.get('state_dir','/run/k248-userdata'));o.mkdir(mode=0o700);state=dict(state='preflight',terminal=False,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21],bytes_generated=0);tail=bytearray();started=False
def guard():
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==cfg['boot_id'] and Path('/run/k248-rescue-boot-id-private.txt').read_text().strip()==cfg['boot_id']
 assert Path('/sys/class/block/sda16/ro').read_text().strip()=='1'
 assert not any(l.split()[0]=='/dev/sda16' for l in Path('/proc/mounts').read_text().splitlines())
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
save()
try:
 guard();state['state']='checking_source_read_only';save()
 if cfg.get('source_fsck_state'):
  prior=json.loads(Path(cfg['source_fsck_state']).read_text());assert prior['source_fsck_exit_code']==0
  state['source_fsck_reused_same_read_only_boot']=True
 else:
  with (o/'fsck-source-private.log').open('xb') as log:x=subprocess.run(['fsck.f2fs','--dry-run','--no-kernel-check','-f','/dev/sda16'],stdout=log,stderr=log,timeout=1200)
  assert x.returncode==0,'Source fsck did not pass; do not format or flash'
 state.update(source_fsck_exit_code=0,state='ready');save()
 class Handler(http.server.BaseHTTPRequestHandler):
  protocol_version='HTTP/1.1'
  def log_message(self,*args):pass
  def do_GET(self):
   global started,tail
   guard();fields=self.path.split('/')
   if len(fields)!=3 or not hmac.compare_digest(fields[1],cfg['token']) or fields[2]!='userdata.pcl.zst':self.send_error(404);return
   if started:
    match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers.get('Range',''))
    if state['state']!='complete' or not match:self.send_error(409);return
    start=int(match[1]);total=state['bytes_generated'];end=min(total-1,int(match[2])) if match[2] else total-1;base=total-len(tail)
    if not base<=start<=end<total:self.send_error(416);return
    self.send_response(206);self.send_header('Content-Length',str(end-start+1));self.send_header('Content-Range',f'bytes {start}-{end}/{total}');self.send_header('Connection','close');self.end_headers();self.wfile.write(tail[start-base:end-base+1]);return
   assert not self.headers.get('Range');started=True;state.update(state='streaming',started_monotonic=time.monotonic());save();self.connection.settimeout(10);self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Connection','close');self.end_headers();digest=hashlib.sha256();last=0;wire_ok=True
   with (o/'partclone-stderr-private.log').open('xb') as err1,(o/'zstd-stderr-private.log').open('xb') as err2:
    part=subprocess.Popen([cfg.get('partclone_binary','partclone.f2fs'),'-c','-s','/dev/sda16','-o','-','-q','-L',str(o/'partclone-private.log')],stdout=subprocess.PIPE,stderr=err1)
    compressor=subprocess.Popen(['zstd','-T2','-3','--check','-q','-c'],stdin=part.stdout,stdout=subprocess.PIPE,stderr=err2);part.stdout.close()
    try:
     while True:
      b=compressor.stdout.read(65536)
      if not b:break
      digest.update(b);state['bytes_generated']+=len(b);tail.extend(b)
      if len(tail)>4*1024*1024:del tail[:len(tail)-4*1024*1024]
      if wire_ok:
       try:self.wfile.write(b)
       except (OSError,TimeoutError):wire_ok=False;state['network_stream_interrupted']=True
      if time.monotonic()-last>2:save();last=time.monotonic()
     pc=part.wait(timeout=60);zc=compressor.wait(timeout=60);assert pc==zc==0,(pc,zc)
    finally:
     for child in [part,compressor]:
      if child.poll() is None:child.terminate();child.wait(timeout=30)
   guard();(o/'tail-private.bin').write_bytes(tail);state.update(state='complete',sha256=digest.hexdigest(),partclone_exit_code=pc,zstd_exit_code=zc,tail_bytes=len(tail),elapsed_seconds=round(time.monotonic()-state['started_monotonic'],2));save()
 class Server(socketserver.TCPServer):
  allow_reuse_address=False
  def handle_error(self,request,client_address):raise RuntimeError('Userdata request handler failed') from sys.exception()
 with Server((cfg['bind_address'],cfg['port']),Handler) as server:
  server.timeout=1;deadline=time.monotonic()+10800
  while time.monotonic()<deadline and not (o/'stop-request').exists():server.handle_request()
 state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 (o/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
