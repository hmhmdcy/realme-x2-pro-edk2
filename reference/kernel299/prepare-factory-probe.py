"""Translate verified factory BLS facts to existing WB subtraction/gain fields."""
from pathlib import Path
import hashlib,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel298'
proof=json.loads((HERE/'factory-bls-export-validation.json').read_text());assert proof['independent_reader_and_direct_decoder_agree']
offset=proof['all_ife_offsets_u14'];assert offset==960
level=(offset*65535+8191)//16383;assert level==3840 and (level*16383+32767)//65535==offset
factory_q11=(16384*2048)//(16384-offset);gain_q10=(factory_q11+1)//2;gain_q7=(gain_q10+4)//8
assert (factory_q11,gain_q10,gain_q7)==(2175,1088,136)
profile=dict(stage=299,sensor='imx319',source_module_name='sunny_imx319',source_sha256=proof['source_sha256'],
 individual_module_vendor_not_verified=True,individual_dark_calibration=False,black_offset_u14=offset,common_subtraction_u16=level,
 factory_normalization_q11=factory_q11,common_normalization_gain_q10=gain_q10,effective_wb_gain_q7=gain_q7,
 normalization_relative_quantization_error=(gain_q7/128)/(factory_q11/2048)-1,
 normalization_is_explicit_userspace_gain=True,driver_bls_scale_remains_unity=True,
 valid_for_experimental_hardware_profile_only=True,software_sensor_black_level_not_overridden=True,installed_in_product_package=False)
(HERE/'factory-profile-validation.json').write_text(json.dumps(profile,indent=2)+'\n')
# No firmware implementation copied: use the already-tested standard MC/V4L2 tool.
s=(OLD/'samurai-blc.c').read_text()
a=s.index(' static const unsigned levels[7]');b=s.index(' struct params_envelope envelope=',a)
s=s[:a]+f''' if(phase>=1&&phase<=3)wb.g_sub=wb.b_sub=wb.r_sub={level};
 if(phase==2||phase==3)wb.g_gain=wb.b_gain=wb.r_gain={gain_q10};
 if(phase==3){{wb.r_gain={gain_q10//2};wb.b_gain={gain_q10*3//4};}}
 if(phase==4){{wb.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;wb.header.size=sizeof(wb.header);}}
 if(phase==5)wb.g_sub=wb.b_sub=wb.r_sub=4096;
 struct camss_params_aec_bhist bh={{.header={{CAMSS_PARAMS_AEC_BHIST,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(bh)}},.width=2104,.height=1560}};
'''+s[b:]
s=s.replace('frame<126','frame<54')
a=s.index('  if(frame&&frame%9==0){',s.index(' for(unsigned frame='));b=s.index('  struct pollfd p={.fd=video',a)
s=s[:a]+'''  if(frame&&frame%9==0)if(queue_params(wb_phase,true)||dequeue_params(wb_phase))goto cleanup;
'''+s[b:]
# This shorter probe doesn't stop/restart the metadata stream.
a=s.index('static int stats_drain_stopped(void)');b=s.index('static int stats_close(void)',a);s=s[:a]+s[b:]
p=HERE/'samurai-factory-bls.c';assert not p.exists();p.write_text(s)
binary=host.PRIVATE/'factory-bls-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'factory-probe-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/not-used'],capture_output=True).returncode==3
for name in ['native-blc.py','launch-blc.py','poll-blc.py']:
 t=(OLD/name).read_text().replace('blc','factory-bls').replace('k298-factory-bls','k299-factory-bls').replace('k298-tools','k299-tools').replace('stage=298','stage=299')
 if name=='native-blc.py':
  a=t.index(" report['stats_restart_markers']");b=t.index(" report['negative_parameter_cases']",a)
  t=t[:a]+" report['passed']=report['statistics_frames']==54 and ret==0 and report['actual_frames']==54 and report['graph_restored'] and not any(faults.values()) and before==after\n"+t[b:]
  t=t.replace("report['parameter_completions']==8 and len(images)>=13","report['parameter_completions']==6 and len(images)==6")
 if name=='launch-blc.py':
  t=t.replace("p=Path('/var/lib/samurai/k299-tools/factory-bls.part');assert not p.exists();p.write_bytes(b'')", "root=Path('/var/lib/samurai/k299-tools');assert not root.exists();root.mkdir(mode=0o700);p=root/'factory-bls.part';p.write_bytes(b'')")
 (HERE/name.replace('blc','factory-bls')).write_text(t)
(HERE/'factory-bls-tool-validation.json').write_text(json.dumps(dict(stage=299,kernel_build=298,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,wrong_kernel_guard_pass=True,planned_frames=54,planned_phases=6,no_driver_or_uapi_change=True),indent=2)+'\n')
print(json.dumps(profile,indent=2))
