"""Save the focused candidate state and its upstream algorithm provenance."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
build=json.loads((HERE/'build-validation.json').read_text())
sources={}
for name in build['source_files']:
    p=TREE/name
    if name.endswith('camss.mojom'):published=HERE/'camss.mojom'
    elif name=='include/linux/qcom-camss-config.h':
        published=Path('/home/cy122/x2pro-linux/camera307-rgb-kernel/include/uapi/linux/qcom-camss-config.h')
    else:
        published=HERE/('ipa' if name.startswith('src/ipa/') else 'pipeline')/p.name
    if p.read_bytes()!=published.read_bytes():raise RuntimeError('Source differs from built candidate: '+name)
    sources[name]=hashlib.sha256(p.read_bytes()).hexdigest()
upstream=['src/ipa/libipa/awb_grey.cpp','src/ipa/libipa/awb_grey.h','src/ipa/libipa/awb.h']
artifacts=['output/src/libcamera/libcamera.so.0.7.2','output/src/ipa/camss-vfe/ipa_camss_vfe.so',
           'output/src/libcamera/proxy/worker/camss_ipa_proxy']
report={'stage':308,'sdk_tree':str(TREE),'sdk_source_version':'0.7.2',
 'kernel_candidate':'samurai-rgb307 / ba9b36e8f872017ad2a39480a223a3afb76e1488',
 'source_sha256':sources,'reused_upstream_awb_sources':{n:hashlib.sha256((TREE/n).read_bytes()).hexdigest() for n in upstream},
 'candidate_sha256':{n:hashlib.sha256((TREE/n).read_bytes()).hexdigest() for n in artifacts},
 'kernel_dt_sensor_sources_changed':False,'system_install':False,
 'profile_is_formal_individual_calibration':False}
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n')
print('Saved matching candidate sources and reused libipa AwbGrey provenance.')
