"""Run actual driver/IRQ bodies and official DMI64 oracle on host and ARM64."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage433test',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354';directory=kernel/'drivers/media/platform/qcom/camss'
state=json.loads((HERE/'source-state.json').read_text());assert subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()==state['commit']
work=P/'driver-test';(work/'linux/media').mkdir(parents=True,exist_ok=True)
for name in ['linux/qcom-camss-config.h','linux/media/v4l2-isp.h']:shutil.copyfile(kernel/'include/uapi'/name,work/name)
shutil.copyfile(HERE/'driver-test.c',work/'test.c');shutil.copyfile(directory/'camss-vfe-175-gtm.h',work/'camss-vfe-175-gtm.h')
raw=(directory/'camss-vfe-175-gtm.c').read_text();assert raw==(HERE/'camss-vfe-175-gtm.c').read_text();(work/'gtm-driver-body-private.c').write_text('\n'.join(l for l in raw.splitlines() if not l.startswith('#include'))+'\n')
def function(source,needle):
 start=source.index(needle);brace=source.index('{',start);end=brace+1;depth=1
 while depth:depth+=(source[end]=='{')-(source[end]=='}');end+=1
 return source[start:end]+'\n'
common=(directory/'camss-vfe.c').read_text();irq=(directory/'camss-vfe-17x.c').read_text();functions=[]
for needle in ['static u32 vfe_reg_update_mask(', 'static void vfe_reg_update(', 'static inline void vfe_reg_update_clear(']:functions.append(function(irq,needle))
functions.append(function(common,'struct camss_buffer *vfe_params_apply_next('))
for needle in ['static void vfe_isr_sof(', 'static void vfe_isr_reg_update(']:functions.append(function(irq,needle))
(work/'integration-functions-private.c').write_text('\n'.join(functions))
stats=(kernel/'drivers/media/v4l2-core/v4l2-isp.c').read_text();(work/'stats-functions-private.c').write_text(function(stats,'struct v4l2_isp_block_header *\nv4l2_isp_stats_init_block('))
official=(P/'official-cam-cdm-util-private.c').read_text();start=official.index('struct cdm_dmi_cmd {');end=official.index(';',official.index('} __attribute__',start))+1
(work/'official-cdm-functions-private.c').write_text('#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wsign-compare"\n'+official[start:end]+'\n'+function(official,'static int cam_cdm_util_swd_dmi_write(')+'#pragma GCC diagnostic pop\n')
assert '\tvfe_175_gtm_params(vfe, block);' in (directory/'camss-vfe-175-pixel.c').read_text()
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');arm=sdk/'private/camss433-gtm-driver';shutil.copytree(work,arm,dirs_exist_ok=True)
flags=['-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation','-fno-strict-aliasing'];rows=[]
fixtures=sorted((P.parent/'kernel432').glob('*-adrc-lut-private.bin'));assert len(fixtures)==9
for arch in ['host','aarch64']:
 if arch=='host':command=['gcc',*flags,'-fsanitize=address,undefined','-no-pie','-I'+str(work),str(work/'test.c'),'-o',str(work/'test-host')]
 else:command=['chroot',str(sdk),'gcc',*flags,'-I/private/camss433-gtm-driver','/private/camss433-gtm-driver/test.c','-o','/private/camss433-gtm-driver/test-aarch64']
 q=subprocess.run(command,capture_output=True);(P/('driver-'+arch+'-build-private.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 for fixture in fixtures:
  if arch=='host':launch=[str(work/'test-host'),str(fixture)]
  else:shutil.copyfile(fixture,arm/'native-lut-private.bin');launch=['chroot',str(sdk),'/private/camss433-gtm-driver/test-aarch64','/private/camss433-gtm-driver/native-lut-private.bin']
  q=subprocess.run(launch,capture_output=True,timeout=20);(P/('driver-'+arch+'-'+fixture.stem+'-private.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(fixture.name,q.stderr.decode());assert b'GTM_DRIVER_PASS' in q.stdout
 rows.append(dict(architecture=arch,stock_lut_cases=len(fixtures),passed=True));print(json.dumps(rows[-1]),flush=True)
r=dict(stage=433,source_commit=state['commit'],architectures=rows,actual_gtm_driver_body=True,actual_param_dequeue_and_pix_reg_update_arm_ack_sof_functions=True,official_gpl_swd_dmi64_function_used_as_oracle=True,canonical_low_then_high_trace_matches=True,all64_inactive_bank_entries_and_unrelated_state_checked=True,old_outstanding_ack_cannot_claim_new_cookie=True,unarmed_ack_cannot_publish=True,queued_second_gtm_deferred_to_fresh_rup=True,late_completed_stats_uses_sof_snapshot=True,explicit_disable_ack_and_stop_state_clear_checked=True,duplicate_gtm_payload_rejected=True,invalid_field_cases_each=200,host_asan_ubsan=True,kernel_irqs_and_mmio_simulated=True,physical_hardware_verified=False,phone_accessed=False,passed=True)
(HERE/'driver-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
