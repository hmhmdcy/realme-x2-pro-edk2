from pathlib import Path
import difflib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel379');P.mkdir(mode=0o700,exist_ok=True)
old=HERE.parent/'kernel378'
(HERE/'host.py').write_text((old/'host.py').read_text().replace('kernel378','kernel379').replace('host377','host378').replace('kernel377','kernel378'))
# The 378 transaction ended on a different boot; adopt its verified recovery guard.
h=old/'host.py';s=h.read_text()
if 'def ssh(' not in s:
 s=s.replace('import importlib.util','import importlib.util,json,shlex').replace('ssh=previous.ssh\n','')
 s+='\ndef ssh(command,**kwargs):\n adoption=PRIVATE/"recovered-boot-adoption-private.json"\n if not adoption.exists():return previous.ssh(command,**kwargs)\n raw_ssh("cmp -s /proc/sys/kernel/random/boot_id "+shlex.quote(json.loads(adoption.read_text())["guard_path"]),timeout=15)\n return raw_ssh(command,**kwargs)\n'
 h.write_text(s)
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent=json.loads((old/'source-state.json').read_text())['commit'];assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
names=['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c'];patch=''
for name in names:
 before=(source/relative/name).read_text();after=before
 if name==names[0]:
  anchor='\t\ta5->session_payload_status = get_unaligned_le32(a5->message + 32);'
  assert before.count(anchor)==1
  after=before.replace(anchor,'\t\t/* MAP/UNMAP callbacks only initialize the ACK header. Their\n\t\t * 12-byte tail retains allocator contents, not a status word.\n\t\t */\n\t\ta5->session_payload_status =\n\t\t\t(a5->session_opcode == IPE_CONFIG_IO ||\n\t\t\t a5->session_opcode == IPE_DESTROY) ?\n\t\t\tget_unaligned_le32(a5->message + 32) : 0;')
 (P/(name+'.before')).write_text(before);(P/(name+'.proposed')).write_text(after)
 patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+str(relative/name),tofile='b/'+str(relative/name)))
(HERE/'ack-status.patch').write_text(patch);(HERE/names[2]).write_text((P/(names[2]+'.proposed')).read_text())
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=379,parent=parent,changed=[names[0]],map_unmap_ack_tail_is_unspecified=True,installed=False),indent=2)+'\n')
for name in ['check-session.py','check-owner.py','check-encoder.py','check-worker.py','check-dispatch.py','owner-regression.c','boot-worker.py','snapshot-collector.py','firmware-context-validation.json','preflight.py','launch-boot.py','poll-boot.py','build-intree.py','apply-source.py']:
 s=(old/name).read_text().replace('stage=378','stage=379').replace('stage = 378','stage = 379').replace('k378-boot-','k379-boot-').replace('Prepared378','Prepared379').replace("HERE.parent/'kernel377/live-overlay-state-private.json'","HERE.parent/'kernel378/live-overlay-state-private.json'")
 if name=='launch-boot.py':s=s.replace("P.parent/'kernel377/recovered-boot-adoption-private.json'","P.parent/'kernel378/recovered-boot-adoption-private.json'")
 if name=='apply-source.py':s=s.replace('samurai-a5-command-window378','samurai-a5-ack-status379').replace('media: camss: keep command memory outside firmware debug queue mappings','media: camss: validate only initialized fields in memory mapping ACKs').replace("'session-validation.json'","'session-validation.json'").replace("'stage=377','stage=378'","'stage=377','stage=379'").replace("P.parent/'kernel377/live-overlay-state-private.json'","P.parent/'kernel378/live-overlay-state-private.json'")
 (HERE/name).write_text(s)
# Copy validated independent models; serialize bytes unchanged from 377.
for name in ['hal-io-validation.json','encoder-validation.json']:(HERE/name).write_bytes((old/name).read_bytes())
s=(old/'session-regression.c').read_text();anchor='bytes=44;put_unaligned_le32(IPE_ASYNC_DIRECT_ACK,reply+4);';assert s.count(anchor)==1
s=s.replace(anchor,'memset(reply+32,0xa5,12);'+anchor);(HERE/'session-regression.c').write_text(s)
s=(HERE.parent/'kernel377/check-firmware-io.py').read_text().replace('stage=377','stage=379')
s=s.replace("if pc==0x6cc0:result=HEAP+state['alloc'];state['alloc']+=(a+15)&~15","if pc==0x6cc0:\n   result=HEAP+state['alloc'];state['alloc']+=(a+15)&~15;uc.mem_write(result,bytes([0xa5])*a)")
s=s.replace("assert struct.unpack_from('<I',reply,32)[0]==0","assert struct.unpack_from('<I',reply,32)[0]==(0 if operation=='config' else 0xa5a5a5a5)")
s=s.replace('no_hardware_execution_claim=True,passed=True','allocator_returns_dirty_bytes=True,map_unmap_tail_preserves_allocator_bytes_and_is_not_status=True,no_hardware_execution_claim=True,passed=True')
(HERE/'check-firmware-io.py').write_text(s)
(P/'live-overlay-state-private.json').write_bytes((P.parent/'kernel378/live-overlay-state-private.json').read_bytes())
print('Prepared opcode-specific ACK status validation and dirty-allocation firmware oracle.')
