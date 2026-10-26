"""Narrow, default-off final transport boundary; no installed source edit."""
from pathlib import Path
import difflib,hashlib,json,re
HERE=Path(__file__).resolve().parent;OWNER=HERE.parent/'apsd-phy-client-candidate';BUS=HERE.parent/'apsd-input-backend-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
header=(BUS/'samurai-apsd-backend.h').read_text()
header=replace(header,'struct samurai_apsd_bus_ops {',(HERE/'attempt-api.inc').read_text()+'\nstruct samurai_apsd_bus_ops {')
header=replace(header,'int (*rerun_once)(void *ctx, u64 epoch);','int (*rerun_once)(void *ctx, const struct samurai_apsd_attempt *attempt,\n\t\t\tstruct samurai_apsd_transfer_result *result);')
inc=(BUS/'samurai-apsd-input.inc').read_text()
start=inc.index('static int samurai_usb_apsd_rerun(');end=inc.index('static const struct samurai_apsd_bus_ops',start)
reader=inc[:start]
reader=replace(reader,'static int samurai_usb_apsd_read(void *ctx,','static int samurai_usb_apsd_sample_locked(struct samurai_usb_input *input,')
reader=replace(reader,'\tstruct samurai_usb_input *input = ctx;\n','')
reader=replace(reader,'\tmutex_lock(&input->lock);\n','')
reader=replace(reader,'\tmutex_unlock(&input->lock);\n','')
wrapper='''static int samurai_usb_apsd_read(void *ctx, struct samurai_apsd_bus_sample *sample)
{
 struct samurai_usb_input *input = ctx;
 int ret;
 mutex_lock(&input->lock);
 ret = samurai_usb_apsd_sample_locked(input, sample);
 mutex_unlock(&input->lock);
 return ret;
}

'''
inc=reader+wrapper+(HERE/'transfer-functions.inc').read_text()+'\n\n'+inc[end:]
source=(OWNER/'samurai-apsd-owner.c').read_text()
source=replace(source,'\tstruct samurai_apsd_once once;','''\tstruct samurai_apsd_once once;
 struct samurai_apsd_bus_sample last_sample;
 struct samurai_apsd_attempt attempt;
 struct samurai_apsd_transfer_result transfer;
 void *attempt_bus;
 struct samurai_pd5v *attempt_pd;
 u64 attempt_generation;
 bool attempt_active;''')
source=replace(source,'\tret = o->bus->read_sample(o->bus_ctx, &sample);\n\tif (ret)\n\t\treturn ret;','\tret = o->bus->read_sample(o->bus_ctx, &sample);\n\tif (ret)\n\t\treturn ret;\n\to->last_sample = sample;')
source=replace(source,'static void owner_work(struct work_struct *work)',(HERE/'owner-attempt-functions.inc').read_text()+'\n\nstatic void owner_work(struct work_struct *work)')
source=replace(source,'''			ret = o->bus->rerun_once(o->bus_ctx, o->once.epoch);
			samurai_apsd_write_done(&o->once, o->once.epoch,
					owner_now_ms(), ret);''','\t\t\tret = owner_transfer(o);')
source=replace(source,'route + final-write contract absent','route capability absent')
files={'samurai-apsd-backend.h':header.encode(),'samurai-apsd-input.inc':inc.encode(),'samurai-apsd-owner.c':source.encode(),
       'samurai-usb-input.c':(BUS/'samurai-usb-input.c').read_bytes(),
       'samurai-usb-input-decode.h':(BUS/'samurai-usb-input-decode.h').read_bytes(),
       'samurai-apsd-owner.h':(OWNER/'samurai-apsd-owner.h').read_bytes()}
for name,raw in files.items():
    path=HERE/name
    if path.exists():assert path.read_bytes()==raw,name
    else:path.write_bytes(raw)
result=dict(prepared=True,phone_accessed=False,attempt_gate_enabled=False,
    files={name:sha(raw) for name,raw in files.items()},
    original_owner_sha256=sha((OWNER/'samurai-apsd-owner.c').read_bytes()),original_bus_include_sha256=sha((BUS/'samurai-apsd-input.inc').read_bytes()))
(HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(prepared=True,attempt_gate_enabled=False)))
