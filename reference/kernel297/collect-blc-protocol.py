"""Pin BLS register facts and units without adopting another module's tuning."""
from pathlib import Path
import hashlib,json,re,urllib.request
import host
HERE=Path(__file__).resolve().parent
commit='36fc163a534963a5b3af52186af5efcc63401ad2'
paths=['camx/src/hwl/isphwsetting/titan17x/camxifebls12titan17x.cpp',
       'camx/src/hwl/isphwsetting/titan17x/camxifebls12titan17x.h',
       'camx/src/hwl/iqsetting/bls12setting.cpp','camx/src/hwl/iqsetting/bls12setting.h']
sources=[]
for name in paths:
 url='https://raw.githubusercontent.com/comprehensive9/vendor_qcom_proprietary/'+commit+'/'+name
 p=host.PRIVATE/(Path(name).name+'-reference-private')
 assert not p.exists()
 with urllib.request.urlopen(url,timeout=30) as response:b=response.read()
 assert 1000<len(b)<100000 and Path(name).name.encode() in b
 p.write_bytes(b)
 sources.append(dict(url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),git_blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()))
header=Path('/mnt/e/edk2-samurai-out/kernel296/titan170-ife-source-0-private.h').read_text()
names=['regIFE_IFE_0_VFE_BLACK_LEVEL_CFG','regIFE_IFE_0_VFE_BLACK_LEVEL_THRESHOLD_0','regIFE_IFE_0_VFE_BLACK_LEVEL_THRESHOLD_1',
       'IFE_IFE_0_VFE_MODULE_LENS_EN_BLACK_LEVEL_EN_MASK','IFE_IFE_0_VFE_BLACK_LEVEL_CFG_OFFSET_MASK',
       'IFE_IFE_0_VFE_BLACK_LEVEL_CFG_SCALE_MASK','IFE_IFE_0_VFE_BLACK_LEVEL_CFG_SCALE_SHIFT']
defines={name:int(re.search(r'^#define '+name+r'\s+(0x[0-9a-f]+|\d+)',header,re.M)[1],0) for name in names}
assert defines['regIFE_IFE_0_VFE_BLACK_LEVEL_CFG']==0x6b0 and defines['IFE_IFE_0_VFE_MODULE_LENS_EN_BLACK_LEVEL_EN_MASK']==0x800
iq=(host.PRIVATE/'bls12setting.h-reference-private').read_text()
assert re.search(r'BLS12_SCALE_Q_FACTOR\s*=\s*11;',iq)
report=dict(stage=297,sources=sources,generated_header_sha256=hashlib.sha256(header.encode()).hexdigest(),numeric_register_protocol=defines,
            scale_fractional_bits=11,offset_bits=14,scale_register_bits=17,threshold_channels=['GR','GB','R','B'],
            module_specific_black_level_not_inferred_from_other_phone=True,scene_intercept_not_used_as_calibration=True,
            kernel_implementation_pending=True,physical_black_level_calibration_pending=True,
            scope='Fixed public Titan17x hardware-setting references; not Realme factory calibration or proof of full tuning availability')
(HERE/'blc-protocol-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=297,pinned_sources=len(sources),bls_cfg=hex(defines[names[0]]),scale_fractional_bits=11,implementation_and_calibration_pending=True)))
