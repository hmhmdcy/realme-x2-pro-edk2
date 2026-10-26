"""Test the documented Gamma clock override during DMI reads without changing LUTs."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent
h=(ROOT/'dmi-sequential.h').read_text()
h=h.replace('printf("DMI_BEGIN cfg=', 'uint32_t saved_cgc=mmio_read(base,0x34);\n mmio_write(base,0x34,saved_cgc|8u);\n printf("GAMMA_CGC before=%08x active=%08x\\n",saved_cgc,mmio_read(base,0x34));\n printf("DMI_BEGIN cfg=')
h=h.replace('mmio_write(base,0xc24,saved_cfg);mmio_write(base,0xc28,saved_addr);','mmio_write(base,0xc24,saved_cfg);mmio_write(base,0xc28,saved_addr);\n mmio_write(base,0x34,saved_cgc);')
h=h.replace('result=(mmio_read(base,0xc24)==saved_cfg&&mmio_read(base,0xc28)==saved_addr)?0:-1;',
 'result=(mmio_read(base,0xc24)==saved_cfg&&mmio_read(base,0xc28)==saved_addr&&mmio_read(base,0x34)==saved_cgc)?0:-1;')
header=ROOT/'dmi-cgc.h';assert not header.exists();header.write_text(h)
s=(ROOT/'samurai-dmi-sequential.c').read_text().replace('"dmi-sequential.h"','"dmi-cgc.h"')
source=ROOT/'samurai-dmi-cgc.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'dmi-cgc-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'dmi-cgc-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
report=dict(stage=289,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),bytes=binary.stat().st_size,qemu_content_self_test=True,
 no_lut_data_writes=True,gamma_cgc_override_only='0x34 bit3',saved_cgc_restored=True,not_run_on_phone=True)
(ROOT/'dmi-cgc-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
worker=(ROOT/'native-dphy-history.py').read_text().replace('k289-dmi-r3','k289-dmi-r4').replace('k289-tools/dmi-sequential','k289-tools/dmi-cgc')
(ROOT/'native-dmi-cgc.py').write_text(worker)
s=(ROOT/'launch-dmi-sequential.py').read_text()
for a,b in [('dmi-sequential-tool-validation','dmi-cgc-tool-validation'),('dmi-sequential-aarch64-private','dmi-cgc-aarch64-private'),('native-dmi-sequential.py','native-dmi-cgc.py'),('k289-dmi-r2','k289-dmi-r4'),('dmi-sequential','dmi-cgc')]:s=s.replace(a,b)
(ROOT/'launch-dmi-cgc.py').write_text(s)
s=(ROOT/'poll-dmi-sequential.py').read_text().replace('k289-dmi-r2','k289-dmi-r4').replace('dmi-sequential','dmi-cgc').replace('gamma-lut-sequential','gamma-lut-cgc')
(ROOT/'poll-dmi-cgc.py').write_text(s)
print(json.dumps(report,indent=2))
