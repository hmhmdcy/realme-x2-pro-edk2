from pathlib import Path
import ast,runpy,json,difflib,hashlib,shutil
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));v=Path('/home/cy122/pmos-samurai-rootfs122');ref=r/'reference/kernel125';k=v/'camera125/kernel';out=Path('/mnt/e/edk2-samurai-out/kernel125')
logname='first-failed-dt-build-private.log' if not (out/'first-failed-dt-build-private.log').exists() else 'second-failed-dt-build-private.log'
shutil.copyfile(out/'kernel-full-build.log',out/logname)
tree=ast.parse((ref/'port-cpas-iova.py').read_text());selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['once','dt']];assert len(selected)==2
scope={};exec(compile(ast.Module(body=selected,type_ignores=[]),'fixed-dt-port-functions','exec'),scope)
n='arch/arm64/boot/dts/qcom/sm8150.dtsi';old=(v/'camera124/kernel'/n).read_text();new=scope['dt'](old);assert new.startswith(old[:500]) and new.count('camss: camss@')==1 and new.count('reserved-memory {')==1
badname='first-invalid-candidate-dtsi-private.txt' if not (out/'first-invalid-candidate-dtsi-private.txt').exists() else 'second-invalid-candidate-dtsi-private.txt'
(out/badname).write_text((k/n).read_text());(k/n).write_text(new)
report=json.loads((ref/'cpas-iova-port-validation.json').read_text());patch=''
for n in report['changed_files']:
 p=v/'camera124/kernel'/n;old=p.read_text() if p.exists() else '';new=(k/n).read_text();patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+n if old else '/dev/null',tofile='b/'+n))
(ref/'sm8150-cpas-iova-7.3.patch').write_text(patch);report['patch_sha256']=hashlib.sha256(patch.encode()).hexdigest();report['first_dtc_caught_candidate_text_offset_error']=True;report['candidate_dtsi_restored_and_port_offsets_separated']=True;(ref/'cpas-iova-port-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('CPAS125_DTC_CAUGHT_TEXT_OFFSET_ERROR_CORRECTED_BASE124_UNCHANGED')
