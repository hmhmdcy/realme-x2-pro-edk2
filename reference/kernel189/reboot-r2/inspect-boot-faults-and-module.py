from pathlib import Path
import json
import host

code='''from pathlib import Path
import hashlib,json,os,struct,subprocess
log=subprocess.check_output(['dmesg'],text=True)
patterns=dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',dpu='Frame done timeout',asoc='ASoC error',
 irq_read='Failed to read IRQ status',qca_setup='QCA Failed',bluetooth_reassembly='Frame reassembly failed',slpi_start_timeout='2400000.remoteproc: start timed out')
counts={k:log.count(v) for k,v in patterns.items()}
def note(raw):
 off=struct.unpack_from('<Q',raw,40)[0];size,count,idx=struct.unpack_from('<HHH',raw,58)
 rows=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*size) for i in range(count)]
 strings=raw[rows[idx][4]:rows[idx][4]+rows[idx][5]]
 row=next(r for r in rows if strings[r[0]:].split(b'\\0',1)[0]==b'.note.gnu.build-id')
 return raw[row[4]:row[4]+row[5]]
root=Path('/usr/lib/modules')/os.uname().release
actual=Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes()
candidate=(root/'kernel/drivers/misc/fastrpc.ko').read_bytes()
original=Path('/var/lib/samurai/k189-module-deploy/fastrpc-original-private.ko').read_bytes()
summary=dict(fault_counts=counts,fastrpc_file_sha256=hashlib.sha256(candidate).hexdigest(),
 candidate_loaded=note(candidate)==actual,original_loaded=note(original)==actual,
 fastrpc_reference_count=Path('/sys/module/fastrpc/refcnt').read_text().strip())
Path('/var/lib/samurai/k189r2-startup-inspection/fault-and-module-summary.json').write_text(json.dumps(summary,indent=2)+'\\n')
print(json.dumps(summary))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'boot-fault-and-module-private.json').write_bytes(p.stdout)
summary=json.loads(p.stdout)
(Path(__file__).resolve().parent.parent/'r2-boot-fault-and-module-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(p.stdout.decode())
