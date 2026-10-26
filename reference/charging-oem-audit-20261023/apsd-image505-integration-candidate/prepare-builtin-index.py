"""Generate only the new builtin indices; keep live aliases/dependencies intact."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
HERE=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
module=json.loads((HERE/'input-module-build-result.json').read_bytes());kernel=json.loads((HERE/'kernel-build-r2-result.json').read_bytes())
assert module['passed'] and kernel['passed']
assert module['original_shared_and_baseline_before']==module['original_shared_and_baseline_after'] and module['parent_namespace_unchanged'] and module['parent_mounts_unchanged']
OUT=Path('/home/cy122/charging-management-20261023/apsd-image505-builtin-index-01');assert not OUT.exists();OUT.mkdir()
root=OUT/'root';release='7.3.0-rc6-rmx1931-samurai-k363+';directory=root/'lib/modules'/release;directory.mkdir(parents=True)
for name,row in module['raw_builtin_metadata'].items():
 source=Path(row['path']);assert sha(source)==row['sha256'];shutil.copyfile(source,directory/name)
relative=Path('extra/samurai-charging/samurai-usb-input.ko');ko=directory/relative;ko.parent.mkdir(parents=True)
assert sha(Path(module['module']['path']))==module['module']['sha256'];shutil.copyfile(module['module']['path'],ko)
(directory/'modules.order').write_text(relative.as_posix()+'\n');config=OUT/'empty-modprobe.conf';config.write_bytes(b'')
system_map=Path(kernel['private_output'])/'build-upper/System.map';assert sha(system_map)==kernel['build']['outputs']['System.map']['sha256']
command=['depmod','-b',str(root),'-a','-e','-F',str(system_map),release]
child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE);stdout,stderr=child.communicate();child.wait()
(OUT/'depmod.stdout').write_bytes(stdout);(OUT/'depmod.stderr').write_bytes(stderr)
row=dict(pid=child.pid,terminal=True,returncode=child.returncode,argv=command,diagnostic_bytes=len(stderr));(OUT/'depmod-terminal-private.json').write_text(json.dumps(row,indent=2)+'\n')
assert child.returncode==0 and not stderr,(child.returncode,stderr.decode())
queries={name:'builtin' for name in ['qcom_pmic_tcpm','tcpm','qcom_eud','samurai_eud_route','aux_hpd_bridge','dwc3','phy_qcom_snps_femto_v2','bq27xxx_battery']};queries['samurai_usb_input']='insmod'
results={}
for name,kind in queries.items():
 argv=['modprobe','--dry-run','--show-depends','--ignore-install','-C',str(config),'-d',str(root),'-S',release,name]
 completed=subprocess.run(argv,capture_output=True,text=True);assert completed.returncode==0 and not completed.stderr,(name,completed.returncode,completed.stderr)
 lines=completed.stdout.splitlines();assert len(lines)==1 and lines[0].startswith(kind+' '),(name,lines)
 if kind=='builtin':assert lines[0].split()[1].replace('-','_')==name
 else:assert lines[0].split()[1]==str(ko)
 results[name]=dict(expected=kind,returncode=completed.returncode,stdout=completed.stdout)
selected=['modules.builtin','modules.builtin.modinfo','modules.builtin.bin','modules.builtin.alias.bin']
assert all((directory/name).is_file() for name in selected)
result=dict(passed=True,private_output=str(OUT),isolated_root=str(root),release=release,depmod=row,
 host_kmod_version=subprocess.check_output(['modprobe','--version'],text=True),host_dryrun_queries=results,
 builtin_metadata={name:dict(path=str(directory/name),sha256=sha(directory/name),bytes=(directory/name).stat().st_size) for name in selected},
 phone_test_files={str(path.relative_to(root)):dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size) for path in sorted(root.rglob('*')) if path.is_file()},
 only_four_builtin_metadata_files_for_live_install=True,global_module_alias_and_dependency_indices_to_remain_unchanged=True,
 phone_accessed=False,installed=False)
with (HERE/'builtin-index-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,metadata={name:row['bytes'] for name,row in result['builtin_metadata'].items()},dryrun_queries=len(results))))
