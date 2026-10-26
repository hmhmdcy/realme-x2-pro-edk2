"""Prepare a standard-API-only TPG test for the new kernel, without MMIO fixes or PHY history setup."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel288';PREV=ROOT.parent/'kernel289'
s=(OLD/'samurai-pix-tpg-isolated.c').read_text().replace('7.3.0-rc6-rmx1931-samurai-k279candidate+','7.3.0-rc6-rmx1931-samurai-k290+').replace('"#288 "','"#290 "')
s=s.replace('static uint64_t hash(','''static unsigned char prefill(unsigned char seed,size_t offset) {
 return seed^(unsigned char)(offset*197u+(offset>>8)*31u);
}
static uint64_t hash(''')
s=s.replace('memset(maps[n],fills[n],sizes[n]);','for(size_t i=0;i<sizes[n];i++)((unsigned char *)maps[n])[i]=prefill(fills[n],i);')
s=s.replace('data[n]!=fills[buffer.index]','data[n]!=prefill(fills[buffer.index],n)')
s=s.replace('data[(size_t)y*f->plane_fmt[0].bytesperline+x]!=fills[buffer.index]',
 'data[(size_t)y*f->plane_fmt[0].bytesperline+x]!=prefill(fills[buffer.index],(size_t)y*f->plane_fmt[0].bytesperline+x)')
start=s.index(' if(getenv("SAMURAI_PIX_SNAPSHOT"))');end=s.index('\n uint32_t last_sequence',start);s=s[:start]+s[end:]
source=ROOT/'samurai-standard-tpg-k290.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'standard-tpg-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'standard-tpg-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
negative=subprocess.run(['qemu-aarch64',str(binary),'--capture',str(host.PRIVATE/'wrong-kernel-must-not-exist')],capture_output=True,timeout=10)
assert negative.returncode==3 and not (host.PRIVATE/'wrong-kernel-must-not-exist').exists()
report=dict(stage=290,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,
 source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),qemu_self_test_pass=True,wrong_kernel_guard_passed=True,
 standard_media_v4l2_only=True,no_mmio_access=True,no_temporary_gamma_or_route_fix=True,no_dphy_history_setup=True,not_run_on_phone=True)
(ROOT/'standard-tpg-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
s=(OLD/'native-pix-tpg.py').read_text().replace('k288-tpg-r1','k290-standard-tpg-r1').replace('k288-work','k290-work').replace("'#288 '","'#290 '").replace('samurai-k279candidate+','samurai-k290+').replace('k288-tools/pix-tpg-capture','k290-tools/standard-tpg').replace('stage=288','stage=290')
(ROOT/'native-standard-tpg.py').write_text(s)
s=(OLD/'launch-isolated-pix.py').read_text()
for a,b in [('isolated-pix-tool-validation','standard-tpg-tool-validation'),('pix-isolated-aarch64-private','standard-tpg-aarch64-private'),('pix-tpg-isolated','standard-tpg'),('native-isolated-pix.py','native-standard-tpg.py'),('k288-tpg-r3','k290-standard-tpg-r1'),('k288-work','k290-work'),('k288-tools','k290-tools'),('isolated-pix-worker','standard-tpg-worker'),('isolated-pix-launch','standard-tpg-launch'),('stage=288','stage=290')]:s=s.replace(a,b)
(ROOT/'launch-standard-tpg.py').write_text(s)
s=(OLD/'poll-isolated-pix.py').read_text().replace('isolated-pix-launch','standard-tpg-launch').replace('isolated-pix-poll','standard-tpg-poll').replace('k288-tpg-r3','k290-standard-tpg-r1').replace('tpg-r3-validation','standard-tpg-validation')
(ROOT/'poll-standard-tpg.py').write_text(s)
print(json.dumps(report,indent=2))
