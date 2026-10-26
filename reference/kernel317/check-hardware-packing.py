"""Check the C++ packing against pinned Titan fields for real factory tables."""
from pathlib import Path
import hashlib,json,math,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
header=(P.parent/'kernel296/titan170-ife-source-0-private.h').read_text()
names=['regIFE_IFE_0_VFE_ROLLOFF_CFG','regIFE_IFE_0_VFE_ROLLOFF_GRID_CFG_0',
 'regIFE_IFE_0_VFE_ROLLOFF_STRIPE_CFG_1','IFE_IFE_0_VFE_MODULE_LENS_EN_ROLLOFF_EN_MASK',
 'IFE_IFE_0_VFE_ROLLOFF_CFG_PCA_LUT_BANK_SEL_MASK',
 'IFE_IFE_0_VFE_ROLLOFF_CFG_NUM_MESHGAIN_H_SHIFT','IFE_IFE_0_VFE_ROLLOFF_CFG_NUM_MESHGAIN_V_SHIFT']
defines={name:int(re.search(r'^#define '+name+r'\s+(0x[0-9a-f]+|\d+)',header,re.M)[1],0) for name in names}
banks={name:int(re.search(name+r'\s*=\s*(0x[0-9a-f]+)',header)[1],0) for name in [
 'IFE_IFE_0_VFE_DMI_CFG_DMI_RAM_SEL_ROLLOFF_RAM_L_GR_R_BANK0',
 'IFE_IFE_0_VFE_DMI_CFG_DMI_RAM_SEL_ROLLOFF_RAM_L_GB_B_BANK0',
 'IFE_IFE_0_VFE_DMI_CFG_DMI_RAM_SEL_ROLLOFF_RAM_L_GR_R_BANK1',
 'IFE_IFE_0_VFE_DMI_CFG_DMI_RAM_SEL_ROLLOFF_RAM_L_GB_B_BANK1']}
assert defines[names[0]]==0x6bc and list(banks.values())==[14,15,18,19]
decoded=json.loads((P/'factory-lsc-decoded-private.json').read_text())
tables=[row['gains'] for root in decoded['factory'] for row in root['core']]
channels=['r','gr','gb','b'];input=P/'factory-base-float-mesh.bin'
input.write_bytes(b''.join(struct.pack('<884f',*[v for c in channels for v in table[c]]) for table in tables))
binary=P/'pack-lsc'
compile=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(HERE/'libipa/lens_shading.cpp'),str(HERE/'pack-lsc.cpp'),'-o',str(binary)],capture_output=True)
(P/'lsc-packing-build.log').write_bytes(compile.stdout+compile.stderr);assert not compile.returncode
output=P/'factory-base-packed-titan17x.bin'
q=subprocess.run([str(binary),str(input),str(output)],capture_output=True,check=True)
(P/'lsc-packing.log').write_bytes(q.stdout+q.stderr)
expected=[]
for table in tables:
 quantized={c:[min(8191,max(1024,math.floor(value*1024+0.5))) for value in table[c]] for c in channels}
 # An independent expression from PackIQRegisterSetting: R low/GR high,
 # B low/GB high. The second word's ordering must not be reversed.
 expected += [r+gr*8192 for r,gr in zip(quantized['r'],quantized['gr'])]
 expected += [b+gb*8192 for b,gb in zip(quantized['b'],quantized['gb'])]
actual=output.read_bytes();assert actual==struct.pack('<'+'I'*len(expected),*expected)
test=subprocess.run([str(P/'test-lens-shading')],capture_output=True,check=True)
(P/'lsc-math-test.log').write_bytes(test.stdout+test.stderr)
report=dict(stage=317,library_host_werror_build=True,math_and_asymmetric_channel_tests_passed=True,
 factory_tables_packed=len(tables),words_checked=len(expected),words_per_table=442,
 source_protocol_defines=defines,dmi_banks=banks,gain_bits=13,gain_fractional_bits=10,
 gain_unity_code=1024,gain_max_code=8191,packing_independent_expression_matches=True,
 sensor_geometry_resampling_implemented=False,kernel_parameter_block_implemented=False,
 hardware_programming_performed=False,individual_calibration_applied=False)
(HERE/'lsc-hardware-packing-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
