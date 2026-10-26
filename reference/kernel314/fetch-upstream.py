"""Fetch the upstream CAMSS discussions/patches for local source comparison."""
from pathlib import Path
import gzip,json,urllib.request
import host
url='https://lore.kernel.org/all/20260911062213.195007-1-gjorgji.rosikopulos@oss.qualcomm.com/t.mbox.gz'
try:
 data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'curl/8.0'}),timeout=30).read()
 if data.startswith(b'\x1f\x8b'):data=gzip.decompress(data)
 if b'diff --git' not in data:raise RuntimeError('No patch data in response')
 host.PRIVATE.joinpath('upstream-streams-thread.mbox').write_bytes(data)
 print(json.dumps({'downloaded_bytes':len(data),'url':url}))
except Exception as error:print(type(error).__name__+': '+str(error));raise SystemExit(1)
