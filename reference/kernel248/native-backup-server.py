"""Token protected, USB-bound, read-only partition transfer; all state is private."""
from pathlib import Path
import hashlib,hmac,http.server,json,os,re,signal,socketserver,sys,time,traceback
os.umask(0o077);cfg=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else '/run/k248-backup-config-private.json').read_text());out=Path(cfg.get('state_dir','/run/k248-backup'));out.mkdir(mode=0o700);boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==cfg['boot_id'];state=dict(state='hashing_sources',pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21],terminal=False,verified_sources=[]);failure=None
def save():
 p=out/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(out/'state-private.json')
def identity():assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==cfg['boot_id']
save()
try:
 manifest={}
 for name,entry in cfg['sources'].items():
  identity();h=hashlib.sha256();left=entry['bytes']
  with open(entry['path'],'rb',buffering=0) as f:
   if entry.get('offset'):f.seek(entry['offset'])
   while left:
    b=f.read(min(left,4*1024*1024));assert b;h.update(b);left-=len(b)
  manifest[name]=dict(bytes=entry['bytes'],sha256=h.hexdigest());state['verified_sources'].append(name);save()
 (out/'source-manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
 class Handler(http.server.BaseHTTPRequestHandler):
  protocol_version='HTTP/1.1'
  def log_message(self,*args):pass
  def do_GET(self):
   identity();fields=self.path.split('/')
   if len(fields)!=3 or not hmac.compare_digest(fields[1],cfg['token']) or fields[2] not in cfg['sources']:
    self.send_error(404);return
   name=fields[2];entry=cfg['sources'][name];size=entry['bytes'];start=0;end=size-1;range_=self.headers.get('Range');partial=False
   if range_:
    match=re.fullmatch(r'bytes=(\d+)-(\d*)',range_)
    if not match:self.send_error(416);return
    start=int(match[1]);end=min(size-1,int(match[2])) if match[2] else size-1;partial=True
    if not 0<=start<=end<size:self.send_error(416);return
   self.send_response(206 if partial else 200);self.send_header('Content-Length',str(end-start+1));self.send_header('Content-Type','application/octet-stream');self.send_header('Accept-Ranges','bytes');self.send_header('ETag','"'+manifest[name]['sha256']+'"');self.send_header('Connection','close')
   if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
   self.end_headers()
   with open(entry['path'],'rb',buffering=0) as f:
    f.seek(entry.get('offset',0)+start);left=end-start+1
    try:
     while left:
      b=f.read(min(left,65536));assert b;self.wfile.write(b);left-=len(b)
    except (BrokenPipeError,ConnectionResetError):return
   state['completed_requests']=state.get('completed_requests',0)+1;save()
 class Server(socketserver.TCPServer):allow_reuse_address=False
 with Server((cfg['bind_address'],cfg['port']),Handler) as server:
  server.timeout=1;state.update(state='serving',manifest=manifest,completed_requests=0);save();deadline=time.monotonic()+7200
  while time.monotonic()<deadline and not (out/'stop-request').exists():server.handle_request()
 state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 (out/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
