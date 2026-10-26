"""Keep an active user RPC in the freezer-aware completion wait, not syscall restart."""
from pathlib import Path
import difflib,hashlib,json,subprocess

k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel189')
path=k/'drivers/misc/fastrpc.c';raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='a15e99ea6c420fd5d42ac91d3990fca1cba9762d1a51eacd80ad05383bed7a41'
backup=private/'fastrpc-original-private.c';assert not backup.exists();backup.write_bytes(raw)
text=raw.decode()
text=text.replace('#include <linux/firmware.h>','#include <linux/firmware.h>\n#include <linux/freezer.h>') if '#include <linux/firmware.h>' in text else text.replace('#include <linux/dma-mapping.h>','#include <linux/dma-mapping.h>\n#include <linux/freezer.h>')
assert '#include <linux/freezer.h>' in text
old='\t} else {\n\t\terr = wait_for_completion_interruptible(&ctx->work);\n\t}\n\n\treturn err;'
new='''\t} else {
\t\t/* Keep this RPC and its DMA buffers while the invoking task freezes. */
\t\tdo {
\t\t\terr = wait_for_completion_state(&ctx->work,
\t\t\t\t\t\tTASK_INTERRUPTIBLE | TASK_FREEZABLE);
\t\t} while (err == -ERESTARTSYS && try_to_freeze());
\t}

\treturn err;'''
assert text.count(old)==1
text=text.replace(old,new)
path.write_text(text)
patch=''.join(difflib.unified_diff(raw.decode().splitlines(True),text.splitlines(True),fromfile='a/drivers/misc/fastrpc.c',tofile='b/drivers/misc/fastrpc.c'))
(ref/'fastrpc-freezer-wait.patch').write_text(patch)
p=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict',str(ref/'fastrpc-freezer-wait.patch')],cwd=k,capture_output=True)
(private/'checkpatch-private.log').write_bytes(p.stdout+p.stderr)
report=dict(stage=189,source_before_sha256=hashlib.sha256(raw).hexdigest(),source_after_sha256=hashlib.sha256(text.encode()).hexdigest(),
 checkpatch_exit=p.returncode,qualcomm_unmerged_v3_not_applied=True,
 kernel_completion_freezer_api_used=True,ordinary_signal_semantics_preserved=True,
 kernel_rpc_timeout_unchanged=True,runtime_deployed=False)
(ref/'fastrpc-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));print(p.stdout.decode())
assert p.returncode==0
