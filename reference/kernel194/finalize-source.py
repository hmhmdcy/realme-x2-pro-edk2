from pathlib import Path
import ast,hashlib,json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel194');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior=json.loads((ref/'imx471-source-validation.json').read_text())['prior16_tracked_sources'];assert all(sha(k/n)==h for n,h in prior.items() if n not in ['drivers/of/Kconfig','drivers/of/Makefile'])
assert sha(k/'.config')=='55f1f0a35bd4f20ad70ebd383a8863e05d0b6d53a07c0f0f09fb47cee057913a'
assert sha(k/'arch/arm64/boot/Image')=='bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469' and sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')=='22c1f2ad3c54c52f181c43d343840dc026a05aab499c8fac13dc2476ddded9d3'
assert len((k/'Module.symvers').read_text().splitlines())==16793 and len((k/'modules.order').read_text().splitlines())==770
fields=['drivers/media/i2c/imx471.c','drivers/mfd/qcom-pm8008.c','Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml','drivers/of/Kconfig','drivers/of/Makefile'];patch=subprocess.check_output(['git','diff','--',*fields],cwd=k,text=True)
new=['Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml','drivers/of/samurai-cci-bringup.c','drivers/of/samurai-front-identify.c','drivers/of/samurai-pmic-fixture.c']
for name in new:
 d=subprocess.run(['git','diff','--no-index','--','/dev/null',str(k/name)],capture_output=True,text=True);assert d.returncode==1;patch+=d.stdout.replace('b'+str(k)+'/', 'b/').replace('a'+str(k)+'/', 'a/')
p=ref/'camera-integration-development.patch';p.write_text(patch);subprocess.run(['git','apply','--reverse','--check',str(p)],cwd=k,check=True,capture_output=True)
c=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','--ignore','FILE_PATH_CHANGES','-'],input=patch,capture_output=True,text=True);(out/'camera-combined-checkpatch-private.log').write_text(c.stdout+c.stderr)
assert c.returncode==1 and '0 errors, 3 warnings, 0 checks' in c.stdout and c.stdout.count('WARNING: DT binding docs and includes should be a separate patch.')==3,c.stdout
code=subprocess.check_output(['git','diff','--',*[n for n in fields if not n.startswith('Documentation/')]],cwd=k,text=True)
for name in new:
 if name.startswith('Documentation/'):continue
 d=subprocess.run(['git','diff','--no-index','--','/dev/null',str(k/name)],capture_output=True,text=True);code+=d.stdout.replace('b'+str(k)+'/', 'b/').replace('a'+str(k)+'/', 'a/')
(ref/'camera-development-code.patch').write_text(code)
series={}
for filename in ['camera-development-code.patch','imx471-device-tree-binding.patch','pm8008-initial-address-binding.patch']:
 data=(ref/filename).read_text();p=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','--ignore','FILE_PATH_CHANGES','-'],input=data,capture_output=True,text=True);(out/(filename+'-series-check-private.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout;series[filename]=0
for p in ref.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for p in ref.glob('*.json'):json.loads(p.read_text())
r=dict(stage=194,source_sha256={n:sha(k/n) for n in fields+new},prior14_tracked_sources_unchanged=True,tracked_modified_files=19,new_camera_files=4,combined_patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),reverse_apply_check_passed=True,individual_series_checkpatch_exit=series,combined_collection_binding_separation_warnings=3,combined_collection_is_not_one_submission_patch=True,checkpatch_ignored_file_path_changes_only=True,image_dtb_config_unchanged=True,full_symbols_and_module_order_restored=True,physical_image_capture_complete=False,development_helpers_default_disabled=True)
(ref/'source-final-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
