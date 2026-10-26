from pathlib import Path
import base64,hashlib,json,urllib.request
P=Path('/mnt/e/edk2-samurai-out/kernel244/protocol-source');P.mkdir(mode=0o700,exist_ok=True);results={}
base='https://android.googlesource.com/kernel/msm/+/bf51f920fdef2acb189f5c2e282148279a1f12c9/drivers/char/diag/'
for name in ['diagfwd_cntl.c','diagfwd_socket.c','diagfwd_peripheral.c','diag_masks.c','diagfwd_cntl.h','diagchar.h']:
 try:
  data=urllib.request.urlopen(base+name+'?format=TEXT',timeout=25).read();raw=base64.b64decode(data,validate=True);assert raw.startswith(b'/*')
  (P/name).write_bytes(raw);results[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),url=base+name)
 except Exception as e:results[name]=dict(error=type(e).__name__)
(P/'manifest-private.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
