"""Build a bounded live-stream DMI readback helper from the isolated standard TPG tool."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel288/samurai-pix-tpg-isolated.c').read_text()
s=s.replace('int main(int argc,char **argv) {','#include "dmi-readback.h"\nint main(int argc,char **argv) {')
start=s.index(' if(getenv("SAMURAI_PIX_SNAPSHOT"))')
end=s.index('\n uint32_t last_sequence',start)
s=s[:start]+' if(gamma_readback())goto cleanup;\n'+s[end:]
source=ROOT/'samurai-dmi-readback.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'dmi-readback-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I'+str(ROOT.parent/'kernel288'),'-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'dmi-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10);assert q.returncode==0
report=dict(stage=289,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
 header_sha256=hashlib.sha256((ROOT/'dmi-readback.h').read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),bytes=binary.stat().st_size,
 qemu_content_self_test=True,no_lut_data_writes=True,only_dmi_selector_and_address_writes=True,
 active_stream_owns_clocks=True,state_restored_before_streamoff=True,not_run_on_phone=True)
(ROOT/'dmi-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
