"""Isolate CST offset fields from input color and capture their downstream response."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent
header=r'''/* SPDX-License-Identifier: GPL-2.0-only */
static uint32_t cst_saved[12];static bool cst_saved_valid;
static void cst_probe_set(bool high)
{
 if(!cst_saved_valid){for(unsigned i=0;i<12;i++)cst_saved[i]=mmio_read(gamma_base,0xf30+i*4);cst_saved_valid=true;}
 for(unsigned row=0;row<3;row++){
  mmio_write(gamma_base,0xf30+16*row,0);mmio_write(gamma_base,0xf34+16*row,0);
  mmio_write(gamma_base,0xf38+16*row,high?512u<<16:512u);mmio_write(gamma_base,0xf3c+16*row,1023u<<16);
 }
 mmio_write(gamma_base,0x4ac,1);printf("CST_CONSTANT offset_field=%s value=512 coefficients=zero\n",high?"high":"low");fflush(stdout);
}
static void cst_probe_restore(void)
{
 if(!cst_saved_valid||!gamma_base)return;
 for(unsigned i=0;i<12;i++)mmio_write(gamma_base,0xf30+i*4,cst_saved[i]);mmio_write(gamma_base,0x4ac,1);
 bool equal=true;for(unsigned i=0;i<12;i++)equal&=mmio_read(gamma_base,0xf30+i*4)==cst_saved[i];
 printf("CST_RESTORE registers=%d\n",equal);cst_saved_valid=false;
}
'''
(ROOT/'cst-constant-probe.h').write_text(header)
s=(ROOT/'samurai-gamma-upload-probe.c').read_text().replace('#include "gamma-upload-probe.h"','#include "gamma-upload-probe.h"\n#include "cst-constant-probe.h"')
s=s.replace('frame<9','frame<15').replace('if(!frame||frame==6)','if(!frame||frame==6||frame==12)')
s=s.replace('"%s.corrected",argv[2]','"%s.%s",argv[2],frame==12?"offset-low":"corrected"')
s=s.replace('if(gamma_probe_upload())goto cleanup;','if(gamma_probe_upload())goto cleanup;\n   cst_probe_set(true);')
s=s.replace('if(frame==2){','if(frame==2||frame==8){').replace('   if(gamma_probe_upload())goto cleanup;\n   cst_probe_set(true);',
 '   if(frame==2){if(gamma_probe_upload())goto cleanup;cst_probe_set(true);}else cst_probe_set(false);')
s=s.replace('else if(frame>=3&&frame<6)','else if((frame>=3&&frame<6)||(frame>=9&&frame<12))')
s=s.replace(' gamma_probe_restore();',' cst_probe_restore();gamma_probe_restore();')
source=ROOT/'samurai-cst-constant-probe.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'cst-constant-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'cst-constant-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
report=dict(stage=289,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),header_sha256=hashlib.sha256(header.encode()).hexdigest(),
 binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),bytes=binary.stat().st_size,qemu_content_self_test=True,
 only_synthetic_test=True,cst_zero_matrix_constant_offset_512=True,both_offset_fields_compared=True,registers_restored=True,not_run_on_phone=True)
(ROOT/'cst-constant-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for src,dst in [('native-gamma-upload.py','native-cst-constant.py'),('launch-gamma-upload.py','launch-cst-constant.py'),('poll-gamma-upload.py','poll-cst-constant.py')]:
 s=(ROOT/src).read_text().replace('k289-gamma-r1','k289-cst-r1').replace('gamma-upload','cst-constant')
 (ROOT/dst).write_text(s)
print(json.dumps(report,indent=2))
