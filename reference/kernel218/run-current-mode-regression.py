"""Regression of the changed CPU class against the unchanged current camera."""
from pathlib import Path
import host,json,sys

here=Path(__file__).resolve().parent
assert len(sys.argv) in [2,3] and sys.argv[1] in ['dark-raw','white-rgb']
test=sys.argv[1]
attempt=sys.argv[2] if len(sys.argv)==3 else 'initial'
assert attempt in ['initial','r2']
assert json.loads((here/'cpu-isp-tests-validation.json').read_text())['real_libcamera_cpu_isp_and_dma_heap_test']
root=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert (root/'work/libcamera/src/libcamera-v0.7.2/output/src/libcamera/ipa_pub_key.cpp').read_bytes()==(root/'work/libcamera218/output/src/libcamera/ipa_pub_key.cpp').read_bytes()
source=(here.parent/'kernel214/run-camera-probe.py').read_text()
code=source.split("code=r'''",1)[1].split("'''",1)[0]
changes=[
    ("base=Path('/var/lib/samurai/k214-baseline')","base=Path('/var/lib/samurai/k218-baseline')"),
    ("out=Path('/var/lib/samurai/k214-'+tag)","out=Path('/var/lib/samurai/k218-candidate-"+attempt+"-'+tag)"),
    ("prefix=Path('/run/samurai-camera214-full') if mode=='isolated' else Path('/')","prefix=Path('/run/samurai-camera218-cpu') if mode=='isolated' else Path('/')"),
    ('p=prefix/name',"p=Path('/')/name"),
    ("(base/'apk-installed-before-private.txt')","(base/'installed-before-private.txt')"),
    ("LIBCAMERA_IPA_MODULE_PATH=str(prefix/'usr/lib/libcamera/ipa'),LIBCAMERA_IPA_PROXY_PATH=str(prefix/'usr/libexec/libcamera'),LIBCAMERA_IPA_CONFIG_PATH=str(prefix/'usr/share/libcamera/ipa')",
     "LIBCAMERA_IPA_MODULE_PATH='/usr/lib/libcamera/ipa',LIBCAMERA_IPA_PROXY_PATH='/usr/libexec/libcamera',LIBCAMERA_IPA_CONFIG_PATH='/usr/share/libcamera/ipa'"),
    ('report=dict(stage=214,','report=dict(stage=218,candidate218_core_with_unchanged_r5_signed_ipa=True,'),
    ("if mode=='isolated':\n    env.update(","if mode=='isolated':\n    env['XDG_CONFIG_HOME']=str(prefix/'config-product')\n    env.update("),
    ("user=pwd.getpwuid(10000);sessions=[]",'''product_config=prefix/'config-product/libcamera/configuration.yaml'
for directory in [prefix/'config-product',product_config.parent]:directory.mkdir(mode=0o755,exist_ok=True);directory.chmod(0o755)
shutil.copyfile(config,product_config);product_config.chmod(0o644)
assert product_config.read_bytes()==config.read_bytes()
user=pwd.getpwuid(10000);sessions=[]'''),
]
for old,new in changes:
    assert code.count(old)==1,(old,code.count(old));code=code.replace(old,new)
code=code.replace('__MODE__',repr('isolated')).replace('__TEST__',repr(test))
compile(code,'native-current-mode-regression218','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=110)
(host.PRIVATE/('candidate-'+attempt+'-'+test+'-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout)
assert report['program_exit']==0 and report['library_resolution_verified'] and report['camera_devices_suspended'] and report['media_graph_restored_byte_exact']
assert report['taint']==0 and not any(report['fault_delta'].values())
if test=='white-rgb':assert len(report['frames'])==6 and all(frame['byte_min']==frame['byte_max']==254 for frame in report['frames'])
else:assert len(report['frames'])==6 and all(not f['all_zero'] for f in report['frames']) and all(f['changed_fraction']>0 for f in report['frames'][1:])
report['attempt']=attempt
report['product_cpu_config_explicitly_selected_in_isolated_build']=True
(here/('candidate-'+test+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
