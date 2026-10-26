"""Use the configured DT recipe with isolated paths and semantic comparison."""
from pathlib import Path
import hashlib,importlib.util,json,shlex,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel232');K=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=P/'board-build';out.mkdir(mode=0o700,exist_ok=True)
sp=importlib.util.spec_from_file_location('fdt',R.parent/'kernel211/fdt_compare.py');f=importlib.util.module_from_spec(sp);sp.loader.exec_module(f);parse=f.parser()
old_dtb=P.parent/'kernel219/timing-build/factory-modes.dtb'
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
assert sha(old_dtb)=='a214fd6b2ccb93e5bbb5adc774e7c510398541e8fab286832682cc6bbd76ca42'
old=parse(old_dtb.read_bytes())
recipe=(K/'arch/arm64/boot/dts/qcom/.sm8150-samurai.dtb.cmd').read_text().splitlines()[0].split(':=',1)[1]
commands=[];current=[]
for token in shlex.split(recipe):
 if token==';':commands.append(current);current=[]
 else:current.append(token)
commands.append(current);assert len(commands)==3
proof=json.loads((R/'board-source-validation.json').read_text());results={}
for variant in ['product-p-disabled','experimental-p-identity-only']:
 source=P/'candidate'/(variant+'.dts');assert sha(source)==proof['source_hashes'][source.name]
 base='arch/arm64/boot/dts/qcom/'
 mapping={base+'sm8150-samurai.dts':str(source),base+'.sm8150-samurai.dtb.d.pre.tmp':str(out/(variant+'-pre.d')),
 base+'.sm8150-samurai.dtb.d.dtc.tmp':str(out/(variant+'-dtc.d')),base+'.sm8150-samurai.dtb.dts.tmp':str(out/(variant+'.pp.dts')),
 base+'sm8150-samurai.dtb':str(out/(variant+'.dtb'))}
 def rewrite(value):
  for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])):value=value.replace(a,b)
  return value
 for index,args in enumerate(commands[:2]):
  rewritten=[rewrite(x) for x in args]
  if index==0:rewritten+=['-iquote',str(K/base)]
  r=subprocess.run(rewritten,cwd=K,capture_output=True,timeout=60)
  attempt=len(list(out.glob(variant+'-'+str(index)+'-attempt*-private.log')))+1
  (out/(variant+'-'+str(index)+'-attempt'+str(attempt)+'-private.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-1500:]
 yaml=out/(variant+'.yaml');r=subprocess.run(['dtc','-O','yaml','-o',str(yaml),str(out/(variant+'.pp.dts'))],capture_output=True,timeout=60)
 assert r.returncode==0,r.stderr[-1500:]
 new=parse((out/(variant+'.dtb')).read_bytes());semantic=f.compare(old,new,yaml)
 provider='/camera-pmic-resets'
 q=next(n for n in new if n.endswith('/i2c@894000/pmic@4')) if any(n.endswith('/i2c@894000/pmic@4') for n in new) else next(n for n in new if n.endswith('/pmic@4') and 'qcom,initial-address' in new[n])
 p=q.rsplit('/',1)[0]+'/pmic@8';hog=next(n for n in old if n.endswith('/camera-rear-reset-hog'))
 assert semantic['only_old_nodes']==[hog]
 assert set(semantic['only_new_nodes'])=={provider,p}
 assert {(x['path'],x['property']) for x in semantic['remaining_changed_properties']}=={(q,'reset-gpios'),(q,'resets'),(q,'phandle')},semantic
 handle=lambda node:int.from_bytes(new[node]['phandle'],'big')
 cells=lambda b:[int.from_bytes(b[i:i+4],'big') for i in range(0,len(b),4)]
 assert cells(new[p]['resets'])==[handle(provider),0]
 assert cells(new[q]['resets'])==[handle(provider),1]
 assert cells(new[p]['qcom,address-setup-supplier'])==[handle(q)]
 assert new[p]['status']==(b'disabled\0' if variant=='product-p-disabled' else b'okay\0')
 assert cells(new[p]['reg'])==[8] and cells(new[q]['reg'])==[4] and cells(new[q]['qcom,initial-address'])==[8]
 gp=next(n for n in new if cells(new[provider]['p-reset-gpios'])[0]==int.from_bytes(new[n].get('phandle',b'\0'),'big'))
 old_gpio_handle=cells(old[q]['reset-gpios'])[0]
 assert int.from_bytes(old[gp]['phandle'],'big')==old_gpio_handle
 assert gp.endswith('/pmic@4/gpio@c000'),gp
 assert cells(new[provider]['p-reset-gpios'])==[handle(gp),1,1]
 assert cells(new[provider]['q-reset-gpios'])==[handle(gp),4,1]
 assert not any('supply' in key for key in new[p])
 assert not any(n.startswith(p+'/') for n in new)
 results[variant]=dict(dtb_sha256=sha(out/(variant+'.dtb')),dtb_bytes=(out/(variant+'.dtb')).stat().st_size,
  semantic_delta=semantic,p_q_handles_and_dependency_exact=True,no_p_vin_or_children=True)
report=dict(stage=232,variants=results,production219_image_and_canonical_dtb_untouched=True,
 no_phone_install_or_flash=True,full_pmic_vin_schema_compliance_not_claimed=True)
(R/'board-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
