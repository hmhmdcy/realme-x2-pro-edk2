"""Record pinned hardware facts, separate from per-module calibration."""
from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent
d=json.loads((HERE.parent/'kernel297/blc-protocol-validation.json').read_text())
p=host.PRIVATE.parent/'kernel297/bls_1_2_0.xsd-reference-private'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='5f9caa3c8c46fec4d87235e2dde334454a69c6fb09e962cd45c33e091dc81df1'
d.update(stage=298,kernel_implementation_pending=False,physical_black_level_calibration_pending=True,
 common_interface='camss_params_wb_gain equal g_sub/b_sub/r_sub, normalized U16 full scale',
 offset_mapping='nearest integer(level * 16383 / 65535)',scale_q11=2048,
 no_implicit_range_stretch=True,unequal_subtraction_rejected=True,additive_offsets_rejected=True,
 thresholds_u14=[0,0,0,0],threshold_zero_semantics='No optional below-threshold clipping; actual offset subtraction verified separately on physical sensor pattern',
 module_calibration_not_embedded_in_soc_driver=True)
d['schema_source']=dict(url='https://github.com/comprehensive9/vendor_qcom_proprietary/blob/36fc163a534963a5b3af52186af5efcc63401ad2/chi-cdk/api/chromatix/XSD/isp/bls_1_2_0.xsd',bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),git_blob='f508424a130907ca721061ee8cc48b2d16a33ca1')
(HERE/'blc-protocol-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print('Pinned BLS protocol and calibration boundary recorded.')
