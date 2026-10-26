from pathlib import Path
import importlib.util,json,re,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';parent=json.loads((HERE.parent/'kernel373/source-state.json').read_text())['commit']
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
for name in ['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c','camss-icp-a5-resources.c']:
 (P/(name+'.before')).write_bytes((source/'drivers/media/platform/qcom/camss'/name).read_bytes())
names=['really_probe','driver_bound','device_links_driver_bound','fw_devlink_link_device','device_links_flush_sync_list','device_links_supplier_sync_state_resume','device_links_unblock_consumers','device_link_add','rpm_resume','rpm_suspend','clk_sync_state','icc_sync_state','of_overlay_fdt_apply','dev_pm_domain_sync']
code='''from pathlib import Path
import json
symbols={line.split()[2] for line in Path('/proc/kallsyms').read_text().splitlines() if len(line.split())>=3}
print(json.dumps(dict(kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip(),
 core_absent=not Path('/sys/module/qcom_camss_icp_a5_core').exists(),test_absent=not Path('/sys/module/camss_icp_a5_boot_test').exists(),
 trace_absent=not Path('/sys/module/camss_icp_a5_trace').exists(),symbols={n:n in symbols for n in NAMES})))
'''.replace('NAMES',repr(names))
facts=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert facts['taint']==0 and facts['camss']=='suspended' and facts['core_absent'] and facts['test_absent'] and facts['trace_absent']
config={line.split('=',1)[0]:line.split('=',1)[1] for line in (build/'.config').read_text().splitlines() if '=' in line and line.startswith('CONFIG_')}
report=dict(stage=374,source_commit=parent,source_clean=True,current373_guard_verified=True,**facts,kprobes_config={k:config.get(k) for k in ['CONFIG_KPROBES','CONFIG_KRETPROBES','CONFIG_FUNCTION_TRACER','CONFIG_KALLSYMS']},passed=True)
(HERE/'preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
paths=['drivers/base/dd.c','drivers/base/core.c','include/linux/kprobes.h','Documentation/trace/kprobes.rst']
for relative in paths:
 text=(source/relative).read_text();(P/(Path(relative).name+'.private')).write_text(text)
 if relative.endswith('.c'):
  lines=text.splitlines()
  for i,line in enumerate(lines):
   if re.match(r'.*\b(?:really_probe|driver_bound|device_links_flush_sync_list|fw_devlink_link_device)\(',line) and (line.startswith('static ') or line.startswith('void ')):
    print(relative+':'+str(i+1));print('\n'.join(lines[i:i+14]))
