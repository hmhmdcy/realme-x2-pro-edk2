"""Correct the first proposal using the actual builtin parameter name."""
from pathlib import Path
import hashlib,importlib.util,json,re,shutil,subprocess
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build=json.loads((HERE/'kernel-build-r2-result.json').read_bytes());assert build['passed']
first=json.loads((HERE/'dtb-and-command-result.json').read_bytes());assert first['passed'] and not first['installed']
object_name='arch/arm64/boot/Image'
obj=Path(build['private_output'])/'build-upper'/object_name;assert sha(obj)==build['build']['Image505']['sha256']
names={word.decode() for word in re.findall(rb'[\x20-\x7e]{8,}',obj.read_bytes()) if re.fullmatch(rb'[A-Za-z0-9_]+\.samurai_5v_only',word)}
assert names=={'qcom_pmic_tcpm.samurai_5v_only'},names
parameter=next(iter(names))+'=1';old_parameter='qcom_pmic_typec.samurai_5v_only=1'
old_cmdline=first['candidate_cmdline'];assert old_cmdline.count(old_parameter)==1
cmdline=old_cmdline.replace(old_parameter,parameter)
old_dtb=Path(first['candidate_DTB']['path']);assert sha(old_dtb)==first['candidate_DTB']['sha256']
out=old_dtb.parent.with_name('apsd-image505-dtb-private-02');assert not out.exists();out.mkdir();target=out/'samurai-apsd505-native-private.dtb';shutil.copyfile(old_dtb,target)
command=['fdtput','-t','s',str(target),'/chosen','bootargs',cmdline]
done=subprocess.run(command,capture_output=True,text=True);assert done.returncode==0 and not done.stderr
parser=REF/'charging-ui-audit-20261023/usb-input-irq-board-candidate/inspect-dtb.py'
spec=importlib.util.spec_from_file_location('actual_native505_parameter_correction_decoder',parser);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=m.decode(old_dtb.read_bytes());b=m.decode(target.read_bytes());expected={name:dict(props) for name,props in a['nodes'].items()};expected['/chosen']['bootargs']=cmdline.encode()+b'\0'
assert b['nodes']==expected and b['reserves']==a['reserves']
source=HERE/'PlatformBm.c.candidate';original=source.read_bytes();assert sha(source)==first['BDS_source_sha256']
with (HERE/'history/PlatformBm-before-parameter-name.c.inc').open('xb') as stream:stream.write(original)
assert original.count(old_parameter.encode())==1;changed=original.replace(old_parameter.encode(),parameter.encode());source.write_bytes(changed)
result=dict(passed=True,prior_proposal_not_installed=True,original_incorrect_prefix=old_parameter,
 actual_builtin_parameter=parameter,parameter_proof=dict(actual_Image_path=str(obj),sha256=sha(obj),kernel_Image505=build['build']['Image505']),
 candidate_cmdline=cmdline,instant_current_opt_in_preserved=' bq27xxx_battery.samurai_instant_current=1 ' in cmdline,
 candidate_DTB=dict(path=str(target),sha256=sha(target),bytes=target.stat().st_size),first_proposal_DTB_sha256=sha(old_dtb),
 only_chosen_bootargs_changed_from_first_proposal=True,all_first_proposal_raw_property_and_reserve_checks_retained=True,
 BDS_source_sha256=sha(source),BDS_only_global_cmdline_parameter_corrected=True,phone_written=False,installed=False)
with (HERE/'dtb-and-command-r2-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,actual_builtin_parameter=parameter,DTB=result['candidate_DTB'])))
