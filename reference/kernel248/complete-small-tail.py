"""Complete only a <=64 KiB read-only transfer tail, using strict SSH."""
from pathlib import Path
import importlib.util,json,sys
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel248');name=sys.argv[1];cfg=json.loads((P/'partition-server-config-private.json').read_text());assert name in cfg['sources'] and Path(name).name==name;source=cfg['sources'][name];dest=P/'linux-return-partitions'/name;size=dest.stat().st_size;missing=source['bytes']-size;assert 0<missing<=65536
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel247/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
with dest.open('ab') as output:
 for offset in range(size,source['bytes'],32768):
  n=min(32768,source['bytes']-offset);code="from pathlib import Path;import sys;assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r;f=open(%r,'rb',buffering=0);f.seek(%d);b=f.read(%d);assert len(b)==%d;sys.stdout.buffer.write(b);f.close()"%(cfg['boot_id'],source['path'],offset,n,n);b=host.ssh('python3 -',input=code.encode(),timeout=20).stdout;assert len(b)==n;output.write(b);output.flush()
assert dest.stat().st_size==source['bytes'];print(json.dumps(dict(small_tail_completed_bytes=missing,full_source_sha256_still_must_match=True)))
