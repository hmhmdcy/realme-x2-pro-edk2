"""Prepare a narrow correction to the undeployed typed IPE encoder."""
from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'caller-validation.json').read_text())['actual_ipe_cc_output_type']==2
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='6a6451dd1fa14534e5c805d8ca8e9a588b42016d'
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
base=source/'drivers/media/platform/qcom/camss';patch=[]
for name in ['camss-icp-a5-colour.c','camss-icp-a5-colour.h']:
 old=(base/name).read_text();(P/(name+'.before')).write_text(old)
 if name.endswith('.c'):
  new=old.replace('cc->offset[i] < -4096 || cc->offset[i] > 4095','cc->offset[i] < -1024 || cc->offset[i] > 1023').replace('0x1fff','0x7ff')
  assert new!=old and new.count('0x7ff')==3
 else:
  new=old.replace('offsets are RGB signed integers.','offsets are RGB signed 11-bit integers.\n * The target IPE caller uses HAL output type 2 (type 1 has 13-bit offsets).')
  assert new!=old
 (P/(name+'.proposed')).write_text(new)
 patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/'+name,tofile='b/drivers/media/platform/qcom/camss/'+name))
(HERE/'ipe-offset-width.patch').write_text(''.join(patch))
# Reuse the retained execution environment, but bind the oracle to the caller
# type proved in probe-ipe-cc.py. The full numerical and CDM functions run.
model=(HERE.parent/'kernel396/colour-model.py').read_text().replace("HERE.parent/'kernel380/hal-machine.py'","HERE.parent/'kernel380/hal-machine.py'")
model=model.replace('override+7524','override+5676').replace('override+7580','override+5732').replace('override+7576','override+5728').replace("struct.pack('<IIQ',1,0,regs)","struct.pack('<IIQ',2,0,regs)")
model=model.replace('Target OEM override path supplies an already interpolated CC region.','Actual IPE type 2 OEM override supplies an already interpolated CC region.')
(HERE/'colour-model.py').write_text(model)
check=(HERE.parent/'kernel396/check-colour.py').read_text().replace("'colour396'","'colour398'").replace('stage=396','stage=398').replace('random.Random(396)','random.Random(398)').replace('4096','1024').replace('4095','1023').replace('4097','1025').replace('offset_bits_signed=13','offset_bits_signed=11')
check=check.replace("(HERE/'colour-codec.h').read_bytes()","(P/'camss-icp-a5-colour.h.proposed').read_bytes()").replace("str(HERE/'colour-codec.c')","str(P/'colour.c')")
check=check.replace("oracle=m.Colour();records=[];expected=[];counts={}","oracle=m.Colour();records=[];expected=[];counts={}\n(P/'colour.c').write_bytes((P/'camss-icp-a5-colour.c.proposed').read_bytes())")
check=check.replace('typedef uint32_t u32;','typedef uint32_t u32;typedef uint64_t u64;')
check=check.replace("(include/'camss-icp-a5-colour.h').write_bytes", "(include/'camss-icp-a5-ipe.h').write_text('#define CAMSS_A5_IPE_IQ_BYTES 2584U\\nint camss_a5_ipe_encode_bypass_iq(void *,u32);\\n')\n(include/'camss-icp-a5-colour.h').write_bytes")
# The linked runner only exercises the packet encoder; dead-section collection
# excludes the separately validated parcel function and its bypass dependency.
check=check.replace("'-fsanitize=address,undefined'","'-fsanitize=address,undefined','-no-pie','-ffunction-sections','-Wl,--gc-sections'")
check=check.replace('target_hal_complete_cc13_oem_override_path_executed=True','actual_ipe_caller_type=2,target_hal_complete_cc13_oem_override_path_executed=True,previous_type1_oracle_not_reused=True')
(HERE/'check-colour.py').write_text(check)
parcel=(HERE.parent/'kernel397/check-parcel.py').read_text().replace("old=P.parent/'kernel396'","old=P").replace("HERE.parent/'kernel396/colour-validation.json'","HERE/'colour-validation.json'").replace("P/'camss-icp-a5-ipe.c.before'","P.parent/'kernel397/camss-icp-a5-ipe.c.before'").replace('stage=397','stage=398').replace('4097','1025').replace('4096;reject','1024;reject')
(HERE/'check-parcel.py').write_text(parcel)
print(json.dumps(dict(stage=398,prepared=True,source_unchanged=True,phone_unchanged=True)))
