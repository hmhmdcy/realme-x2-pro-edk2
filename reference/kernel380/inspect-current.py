from pathlib import Path
import json,re,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
code=r'''
from pathlib import Path
import json,struct
dt=Path('/sys/firmware/devicetree/base');icp=dt/'soc@0/icp@ac10000';camss=dt/'soc@0/camss@acb3000';smmu=dt/'soc@0/iommu@15000000'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k378-recovered/boot-id-private.txt').read_bytes()
assert int.from_bytes((smmu/'#iommu-cells').read_bytes(),'big')==2
def spec(node):
 data=(node/'iommus').read_bytes();words=struct.unpack('>'+str(len(data)//4)+'I',data);assert len(words)%3==0
 return [dict(smmu=words[i],sid=words[i+1],mask=words[i+2]) for i in range(0,len(words),3)]
ssc=json.loads(Path('/run/samurai-ssc/state.json').read_text())
print(json.dumps(dict(stage=380,guard378_verified=True,kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 static_icp_status=(icp/'status').read_bytes().rstrip(b'\0').decode(),static_icp_iommus=spec(icp),camss_iommus=spec(camss),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 icp_modules=[p.name for p in Path('/sys/module').glob('*icp*')],temporary_firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 ssc_started=ssc['started'],ssc_stopped=ssc.get('stopped'),ssc_failure=ssc.get('readiness_failure'),phone_mutated=False)))
'''
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
text=(P.parent/'kernel352/oem/sm8150-v2-camera.dtsi').read_text();node=text.split('msm_cam_smmu_icp {',1)[1].split('label = "icp";',1)[0]
oem=[dict(sid=int(a,16),mask=int(b,16)) for a,b in re.findall(r'&apps_smmu\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)',node)]
assert len(oem)==7 and oem[0]==dict(sid=0x2222,mask=0)
overlaps=[dict(icp=a,camss=b) for a in oem for b in d['camss_iommus'] if ((a['sid']^b['sid'])&~(a['mask']|b['mask'])&0xffff)==0]
d.update(oem_combined_icp_sid_specs=oem,proposed_combined_icp_specs_overlap_existing_camss=bool(overlaps),engine_sid_roles_not_individually_identified=True,
 current_a5_only_mapping_does_not_establish_engine_dma=True,actual_frame_submission_this_stage=False,
 normal_camera_capture_reference_stage=379,camera_capture_repeated=False,same_boot_as_camera_reference=True)
d['passed']=bool(d['guard378_verified'] and d['kernel']=='7.3.0-rc6-rmx1931-samurai-k363+' and d['taint']==0 and d['static_icp_status']=='disabled' and not d['icp_modules'] and d['temporary_firmware_absent'] and all(x=='suspended' for x in d['camera_pm'].values()) and not overlaps)
(HERE/'current-state-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));assert d['passed']
