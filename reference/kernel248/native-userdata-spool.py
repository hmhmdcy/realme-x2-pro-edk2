"""Keep the complete compressed image in bounded RAM, then serve resumable ranges."""
from pathlib import Path
import hashlib,hmac,http.server,json,os,re,socketserver,subprocess,sys,time,traceback
os.umask(0o077)
cfg=json.loads(Path(sys.argv[1]).read_text());o=Path(cfg['state_dir']);o.mkdir(mode=0o700)
state=dict(state='preflight',terminal=False,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21],bytes_generated=0)

def guard():
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==cfg['boot_id']==Path('/run/k248-rescue-boot-id-private.txt').read_text().strip()
 assert Path('/sys/class/block/sda16/ro').read_text().strip()=='1'
 assert not any(l.split()[0]=='/dev/sda16' for l in Path('/proc/mounts').read_text().splitlines())

def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')

try:
 guard();assert json.loads(Path('/run/k248-userdata-r2/state-private.json').read_text())['source_fsck_exit_code']==0
 available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 assert available>6*1024**3
 spool=Path(cfg['spool_dir']);spool.mkdir(mode=0o700)
 subprocess.run(['mount','-t','tmpfs','-o','size=5G,nr_inodes=128,mode=0700','k248-backup-spool',str(spool)],check=True)
 image=spool/'userdata.pcl.zst';assert not image.exists();state.update(state='generating_ram_image',source_fsck_exit_code=0,started_monotonic=time.monotonic());save()
 digest=hashlib.sha256();prefix=hashlib.sha256();last=0
 with (o/'partclone-stderr-private.log').open('xb') as e1,(o/'zstd-stderr-private.log').open('xb') as e2,image.open('xb') as target:
  part=subprocess.Popen(['/usr/sbin/partclone.f2fs-ro248','-c','-s','/dev/sda16','-o','-','-q','-L',str(o/'partclone-private.log')],stdout=subprocess.PIPE,stderr=e1)
  z=subprocess.Popen(['zstd','-T2','-3','--check','-q','-c'],stdin=part.stdout,stdout=subprocess.PIPE,stderr=e2);part.stdout.close()
  try:
   while True:
    b=z.stdout.read(1024*1024)
    if not b:break
    offset=state['bytes_generated'];assert offset+len(b)<5*1024**3-64*1024**2
    target.write(b);digest.update(b)
    if offset<cfg['prefix_bytes']:prefix.update(b[:cfg['prefix_bytes']-offset])
    state['bytes_generated']+=len(b)
    if time.monotonic()-last>3:
     save();last=time.monotonic();available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;assert available>512*1024**2
   pc=part.wait(timeout=60);zc=z.wait(timeout=60);assert pc==zc==0,(pc,zc)
  finally:
   for child in [part,z]:
    if child.poll() is None:child.terminate();child.wait(timeout=30)
 guard();assert image.stat().st_size==state['bytes_generated'];state.update(state='complete',sha256=digest.hexdigest(),partclone_exit_code=pc,zstd_exit_code=zc,prefix_bytes=cfg['prefix_bytes'],prefix_sha256=prefix.hexdigest(),elapsed_seconds=round(time.monotonic()-state['started_monotonic'],2));save()
 class Handler(http.server.BaseHTTPRequestHandler):
  protocol_version='HTTP/1.1'
  def log_message(self,*args):pass
  def do_GET(self):
   guard();fields=self.path.split('/')
   if len(fields)!=3 or not hmac.compare_digest(fields[1],cfg['token']) or fields[2]!='userdata.pcl.zst':self.send_error(404);return
   match=re.fullmatch(r'bytes=(\d+)-(\d+)',self.headers.get('Range',''))
   if not match:self.send_error(400);return
   start,end=map(int,match.groups());total=state['bytes_generated']
   if not 0<=start<=end<total or end-start+1>16*1024**2:self.send_error(416);return
   with image.open('rb') as f:f.seek(start);b=f.read(end-start+1)
   self.connection.settimeout(10);self.send_response(206);self.send_header('Content-Length',str(len(b)));self.send_header('Content-Range',f'bytes {start}-{end}/{total}');self.send_header('X-Chunk-SHA256',hashlib.sha256(b).hexdigest());self.send_header('Connection','close');self.end_headers()
   try:
    for pos in range(0,len(b),65536):self.wfile.write(b[pos:pos+65536])
   except (OSError,TimeoutError):pass
 class Server(socketserver.TCPServer):allow_reuse_address=False
 with Server((cfg['bind_address'],cfg['port']),Handler) as server:
  server.timeout=1;deadline=time.monotonic()+7200
  while time.monotonic()<deadline and not (o/'stop-request').exists():server.handle_request()
 state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 (o/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
