"""New handoff-only host harness. Never compile or invoke firmware/SDK."""
from pathlib import Path
import hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def body(text,name,kind):
 pos=text.index(name+' (');start=text.rfind('\n'+kind,0,pos)+1
 assert start>0
 opening=text.index('{',pos);i=opening+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i]
old=(HERE/'PlatformBm.c').read_text();new=(HERE/'PlatformBm.c.candidate').read_text()
for name in ['SamuraiPanelBeforeExitBootServices','SamuraiArmPanelHandoff','SamuraiDisarmPanelHandoff']:
 assert body(old,name,'STATIC')==body(new,name,'STATIC'),name
oldblock=old[old.index('    Status = SamuraiArmPanelHandoff'):old.index('    SamuraiDisarmPanelHandoff')+len('    SamuraiDisarmPanelHandoff (&PanelHandoff);')]
assert oldblock in new
core=body((HERE/'DxeMain--DxeMain.c').read_text(),'CoreExitBootServices','EFI_STATUS')
tpl=body((HERE/'Event--Tpl.c').read_text(),'CoreRestoreTpl','VOID')
(HERE/'core-functions.inc').write_text(core+'\n'+tpl+'\n')
(HERE/'direct-fifo.inc').write_text(body(new,'SamuraiEudComPuts','STATIC')+'\n')
start=new.index('#ifdef SAMURAI_ENABLE_EUD\n    Status = SamuraiArmEudOffHandoff')
end=new.index('    Print (L"[SAMURAI] EfiBootManagerBoot returned',start)
(HERE/'launch.inc').write_text(new[start:end]+';\n')
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer']
build=subprocess.run(['gcc',*flags,str(HERE/'test-boot.c'),'-o',str(HERE/'test-boot')],capture_output=True,text=True)
assert build.returncode==0,build.stderr
run=subprocess.run([str(HERE/'test-boot')],capture_output=True,text=True)
assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
assert not run.stderr
cases=[line.removeprefix('ok: ') for line in run.stdout.splitlines() if line.startswith('ok: ')]
assert len(cases)==12
proof=json.loads((HERE/'candidate-result.json').read_text())
assert len(proof['dt_semantic_changes'])==2 and proof['all_other_dt_properties_byte_exact'] and proof['other_tokens_unchanged']
names=['test-boot.c','eud-handoff-fragment.inc','PlatformBm.c','PlatformBm.c.candidate','core-functions.inc','direct-fifo.inc','launch.inc','run-tests.py','candidate-result.json']
r=dict(passed=True,case_count=len(cases),cases=cases,flags=flags,panel_functions_and_original_call_block_byte_exact=True,
 actual_existing_EDK2_functions=['CoreExitBootServices','CoreRestoreTpl'],
 actual_candidate_functions='all four new helpers plus modified direct FIFO and launch snippet; fake MMIO/BootServices edges',
 files={n:sha(HERE/n) for n in names},stdout=run.stdout,stderr=run.stderr,
 no_full_firmware_compile=True,no_live_tpl_or_hardware_validation=True,SDK_invoked=False,phone_accessed=False,shared_writes=False)
(HERE/'test-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,cases=len(cases))))
