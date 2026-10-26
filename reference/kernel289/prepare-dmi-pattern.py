"""Use position-dependent prefill so valid constant TPG patches do not cause false DMA failures."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent
s=(ROOT/'samurai-dmi-cgc.c').read_text()
needle='static uint64_t hash('
s=s.replace(needle,'''static unsigned char prefill(unsigned char seed,size_t offset) {
 return seed^(unsigned char)(offset*197u+(offset>>8)*31u);
}
'''+needle)
s=s.replace('memset(maps[n],fills[n],sizes[n]);','for(size_t i=0;i<sizes[n];i++)((unsigned char *)maps[n])[i]=prefill(fills[n],i);')
s=s.replace('data[n]!=fills[buffer.index]','data[n]!=prefill(fills[buffer.index],n)')
s=s.replace('data[(size_t)y*f->plane_fmt[0].bytesperline+x]!=fills[buffer.index]',
 'data[(size_t)y*f->plane_fmt[0].bytesperline+x]!=prefill(fills[buffer.index],(size_t)y*f->plane_fmt[0].bytesperline+x)')
source=ROOT/'samurai-dmi-pattern.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'dmi-pattern-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'dmi-pattern-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
report=dict(stage=289,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),header_sha256=hashlib.sha256((ROOT/'dmi-cgc.h').read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),bytes=binary.stat().st_size,qemu_content_self_test=True,
 no_lut_data_writes=True,position_dependent_prefill=True,old_thresholds_retained=True,not_run_on_phone=True)
(ROOT/'dmi-pattern-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for src,dst in [('native-dmi-cgc.py','native-dmi-pattern.py'),('launch-dmi-cgc.py','launch-dmi-pattern.py'),('poll-dmi-cgc.py','poll-dmi-pattern.py')]:
 s=(ROOT/src).read_text().replace('k289-dmi-r4','k289-dmi-r5').replace('dmi-cgc','dmi-pattern').replace('gamma-lut-cgc','gamma-lut-pattern')
 (ROOT/dst).write_text(s)
print(json.dumps(report,indent=2))
