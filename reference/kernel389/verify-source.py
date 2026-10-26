from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;state=json.loads((HERE/'source-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
build=m.mounted_build();source=build.parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
patch=''
for name in state['changed']:
 p=source/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==state['sha256'][name]
 prior=subprocess.run(['git','-C',str(source),'show',state['parent']+':'+name],capture_output=True,text=True)
 assert not prior.returncode or name.endswith(('camss-icp-platform.c','qcom,sm8150-camss-icp.yaml'))
 a=prior.stdout if not prior.returncode else '';b=p.read_text()
 assert b==(P/'changes'/name).read_text()
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name if a else '/dev/null',tofile='b/'+name))
assert patch==(HERE/'platform-and-board.patch').read_text()
assert (source/'drivers/media/platform/qcom/camss/camss-icp-platform.c').read_bytes()==(HERE/'camss-icp-platform.c').read_bytes()
assert (source/'Documentation/devicetree/bindings/media/qcom,sm8150-camss-icp.yaml').read_bytes()==(HERE/'qcom,sm8150-camss-icp.yaml').read_bytes()
module_commit='fcaf366ad1aa788b48ead94fb5e68db85e1d8947';dt_commit=json.loads((HERE/'dt-build-validation.json').read_text())['source_commit']
assert git('diff',module_commit,'HEAD','--','drivers/media/platform/qcom/camss')==''
assert git('diff',dt_commit,'HEAD','--','arch/arm64/boot/dts/qcom/sm8150.dtsi','arch/arm64/boot/dts/qcom/sm8150-samurai.dts')==''
config=(build/'.config').read_text();assert 'CONFIG_VIDEO_QCOM_CAMSS_ICP=y' not in config
assert json.loads((HERE/'intree-build-validation.json').read_text())['passed']
report=dict(stage=389,source_commit=state['commit'],source_clean=True,final_source_matches_proposal_and_parent_patch=True,module_build_source_commit=module_commit,module_sources_unchanged_since_successful_r4=True,dt_build_source_commit=dt_commit,dt_sources_unchanged_since_successful_build=True,shared_build_config_restored=True,phone_deployment_or_formal_driver_runtime_not_claimed=True,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
