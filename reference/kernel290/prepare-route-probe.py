"""Compare the same constant responses with the documented FULL postprocessing gate enabled."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent
h=(ROOT/'cst-response-probe.h').read_text()
h=h.replace('static uint32_t response_saved[12],response_full_saved[2];','static uint32_t response_saved[12],response_full_saved[2],response_frame_saved;')
h=h.replace('response_saved_valid=true;', 'response_frame_saved=mmio_read(gamma_base,0x4c);response_saved_valid=true;',1)
needle=' mmio_write(gamma_base,0x4ac,1);\n printf("RESPONSE_CONFIG'
assert h.count(needle)==1
h=h.replace(needle,' mmio_write(gamma_base,0x4c,response_frame_saved|16u);\n'+needle)
needle='mmio_write(gamma_base,0xe38,response_full_saved[1]);mmio_write(gamma_base,0x4ac,1);'
assert h.count(needle)==1
h=h.replace(needle,'mmio_write(gamma_base,0xe38,response_full_saved[1]);mmio_write(gamma_base,0x4c,response_frame_saved);mmio_write(gamma_base,0x4ac,1);')
h=h.replace('bool equal=mmio_read(gamma_base,0xe18)', 'bool equal=mmio_read(gamma_base,0x4c)==response_frame_saved&&mmio_read(gamma_base,0xe18)')
header=ROOT/'cst-route-probe.h';assert not header.exists();header.write_text(h)
s=(ROOT/'samurai-cst-response.c').read_text().replace('"cst-response-probe.h"','"cst-route-probe.h"').replace('if(!frame){char corrected','if(!frame||frame==6){char corrected')
source=ROOT/'samurai-cst-route.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'cst-route-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'cst-route-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
report=dict(stage=290,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),bytes=binary.stat().st_size,qemu_content_self_test=True,
 fixed_response_phases=15,frames_planned=93,only_added_route_gate='0x4c bit4',route_and_original_registers_restored=True,not_run_on_phone=True)
(ROOT/'cst-route-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for src,dst in [('native-cst-response.py','native-cst-route.py'),('launch-cst-response.py','launch-cst-route.py'),('poll-cst-response.py','poll-cst-route.py')]:
 s=(ROOT/src).read_text().replace('k290-response-r1','k290-route-r1').replace('cst-response','cst-route')
 (ROOT/dst).write_text(s)
print(json.dumps(report,indent=2))
