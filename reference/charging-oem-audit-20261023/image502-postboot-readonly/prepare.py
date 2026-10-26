"""Offline derivation only; does not collect, adopt or create a runtime guard."""
from pathlib import Path
import ast,difflib,hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-management-20261023/image501-postboot-readonly'
ADOPT_OLD=REF/'charging-session-20261023/gauge-image501-adoption-candidate'
ADOPT=HERE.parent/'image502-adoption-candidate'
ACT=HERE.parent/'image502-logdump-activation-candidate'
CONTRACT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image502-notify-materialized-001/prepare-contract.json')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(OLD/'device.py')=='be1b56a1fe38fd46cd8c58e303a8d98c38b6fd154b8db0a32231095b97418eea'
assert sha(OLD/'payload.py')=='8d86687379efb126e015de4af71ed25e28c7ae5e63afaf59ed2347b0e60d5628'
assert sha(ADOPT_OLD/'adopt.py')=='e689b8900e926eacfd045d7a893042afaf65290f727f630239c5f3c5752fd7a7'
assert sha(ACT/'fastboot-operator.py')=='7f473d8698e2e2f83ff768db98de167998a6d7b53e948421b8019fec141d2121'
assert sha(CONTRACT)=='469d2aab76d5af116d52164914f5ac487ace525554ec297ecec861db3c60ba7d'
ADOPT.mkdir(exist_ok=True)

def change(s,a,b):
 assert s.count(a)==1,(a,s.count(a))
 return s.replace(a,b)

device=(OLD/'device.py').read_text()
device=device.replace('CANDIDATE_BOOT','UNCHANGED_BOOT').replace('Image501','Image502').replace('IMAGE501','IMAGE502').replace('LOGDUMP501','LOGDUMP502').replace('#501 ','#502 ').replace('samurai-image501-postboot-readonly-v1','samurai-image502-notify-postboot-readonly-v1')
device=change(device,"ROLLBACK_BOOT='4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf'\n",'')
device=change(device,"IMAGE502='3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'","IMAGE502='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'")
device=change(device,"LOGDUMP502='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'","LOGDUMP502='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'")
device=change(device,"{'candidate_boot_exact':True,'logdump_exact':True,'Image502_binding':'exact full candidate FAT plus frozen Image readback receipt'}","{'unchanged_boot_exact':True,'logdump_exact':True,'Image502_binding':'exact full candidate FAT plus frozen Image readback receipt'}")
device=change(device,"request['guard']['candidate_boot_sha256']==UNCHANGED_BOOT","request['guard']['unchanged_boot_sha256']==UNCHANGED_BOOT and request['guard']['partitions']==['logdump']\n assert request['guard']['candidate_logdump_sha256']==LOGDUMP502 and request['guard']['image502_sha256']==IMAGE502")
(HERE/'device.py').write_text(device)

payload=(OLD/'payload.py').read_text()
payload=change(payload,"PAIR=HERE.parent.parent/'charging-session-20261023/gauge-image501-fastboot-pair-candidate'","PAIR=HERE.parent/'image502-logdump-activation-candidate'")
payload=payload.replace('image501_pair','image502_logdump').replace('samurai-image501-postboot-readonly-v1','samurai-image502-notify-postboot-readonly-v1')
payload=change(payload," assert isinstance(endpoint,str) and endpoint and not any(x.isspace() for x in endpoint)"," assert endpoint=='fe80::62:bcff:fe28:a101%29','root must use the observed peer with the original key'\n check_local()")
payload=change(payload," source=(HERE/'device.py').read_bytes();tree=ast.parse(source)"," pins=json.loads((HERE/'source-pins.json').read_bytes())\n for row in pins.values():assert sha(Path(row['path']).read_bytes())==row['sha256']\n source=(HERE/'device.py').read_bytes();tree=ast.parse(source)")
(HERE/'payload.py').write_text(payload)

adopt=(ADOPT_OLD/'adopt.py').read_text()
adopt=adopt.replace('Image501','Image502').replace('image501','image502').replace('samurai-image502-fastboot-context-v1','samurai-image502-notify-fastboot-context-v1').replace('samurai-image502-postboot-readonly-v1','samurai-image502-notify-postboot-readonly-v1').replace("r'image502-[a-z0-9-]{8,64}'","r'image502-notify-live-001'").replace('#501 ','#502 ')
adopt=change(adopt," context_path,observed=Path(context_path),Path(observed);context=json.loads(context_path.read_bytes())"," context_path,observed=Path(context_path).resolve(),Path(observed).resolve()\n pins,checked=sources();spec=importlib.util.spec_from_file_location('image502_context_gate',pins['activation_operator']['path'])\n operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)\n context=operator.validate_context(context_path)")
adopt=change(adopt,"'candidate_boot_sha256':fixed['candidate_boot_sha256']","'candidate_boot_sha256':fixed['unchanged_boot_sha256']")
adopt=adopt.replace('candidate_pair_verified','boot_and_logdump_verified')
adopt=change(adopt," assert previous['guard_path']==d['postboot_request']['guard']['old_boot_guard_path']\n assert previous['candidate_boot_sha256']==d['postboot_request']['guard']['rollback_boot_sha256']"," check_previous(previous,d)")
point=adopt.index('\ndef adopt(')
adopt=adopt[:point]+'''
def check_previous(previous,d):
 g=d['postboot_request']['guard']
 assert previous['guard_path']==g['old_boot_guard_path']=='/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt'
 assert previous['Image501_verified'] is True and previous['original_key_verified'] is True
 assert previous['candidate_boot_sha256']==g['unchanged_boot_sha256']==d['candidate_boot_sha256']
 assert previous['candidate_logdump_sha256']==g['rollback_logdump_sha256']=='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'
 assert previous['charging_manifest_sha256']==d['manifest']
 assert d['guard']=='/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt' and d['guard']!=previous['guard_path']

'''+adopt[point:]
(ADOPT/'adopt.py').write_text(adopt)

def pin(p):return {'path':str(p),'sha256':sha(p)}
pp={n:pin(p) for n,p in {'original_501_device':OLD/'device.py','original_501_payload':OLD/'payload.py',
 'activation_operator':ACT/'fastboot-operator.py','activation_contract':CONTRACT,
 'Image502_delivery':REF/'charging-ui-audit-20261023/gauge-image502-notify-candidate/delivery.json',
 'FAT502_delivery':REF/'charging-session-20261023/gauge-image502-logdump-candidate/delivery.json'}.items()}
(HERE/'source-pins.json').write_text(json.dumps(pp,indent=2)+'\n')
ap={n:pin(p) for n,p in {'postboot_device':HERE/'device.py','strict_key_transport':REF/'kernel184/host.py',
 'activation_contract':CONTRACT,'activation_operator':ACT/'fastboot-operator.py'}.items()}
(ADOPT/'source-pins.json').write_text(json.dumps(ap,indent=2)+'\n')
for before,after,label in [(OLD/'device.py',HERE/'device.py','device'),(OLD/'payload.py',HERE/'payload.py','payload'),(ADOPT_OLD/'adopt.py',ADOPT/'adopt.py','adopt')]:
 ast.parse(after.read_bytes());patch=''.join(difflib.unified_diff(before.read_text().splitlines(True),after.read_text().splitlines(True),fromfile='501/'+before.name,tofile='502/'+after.name))
 ((ADOPT if label=='adopt' else HERE)/(label+'-501-to-502.patch')).write_text(patch)
print(json.dumps({'derived':True,'device_accessed':False,'guard_or_pointer_created':False}))
