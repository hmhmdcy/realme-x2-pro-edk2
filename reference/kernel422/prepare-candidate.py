"""Create the next candidate and integrate generic numeric sources, not tuning data."""
from pathlib import Path
import json,re,shutil,subprocess
import storage
HERE=Path(__file__).resolve().parent;candidate=storage.candidate();baseline=candidate.parent/'libcamera421-frame-history'
assert json.loads((HERE/'static-validation.json').read_text())['passed']
assert json.loads((HERE/'frame-validation.json').read_text())['passed']
assert not candidate.exists(),'Inspect existing candidate; do not reset it'
free=shutil.disk_usage(candidate.parent).free
assert free>1024**3,free
shutil.copytree(baseline,candidate,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=candidate/'src/libcamera-v0.7.2';dest=tree/'src/ipa/libipa'
inputs={}
for stage,names in [(352,['ltm_inverse_gamma.h','ltm_inverse_gamma.cpp']),
 (407,['ltm_curves.h','ltm_curves.cpp']),(408,['ltm_face_smoothing.h','ltm_face_smoothing.cpp']),
 (409,['ltm_adrc.h','ltm_adrc.cpp']),(412,['tmc11_ltm.h','tmc11_ltm.cpp']),
 (413,['tmc11_generation.h','tmc11_generation.cpp']),(414,['tmc11_tree.h','tmc11_tree.cpp']),
 (415,['tmc_runtime.h','tmc_runtime.cpp']),(416,['tmc_input.h','tmc_input.cpp']),
 (422,['ltm13_static.h','ltm13_static.cpp','ltm13_frame.h','ltm13_frame.cpp'])]:
    for name in names:
        path=HERE.parent/('kernel'+str(stage))/'libipa'/name
        text=path.read_text();text=re.sub(r'"../../kernel\d+/libipa/([^"/]+)"',r'"\1"',text)
        assert not (dest/name).exists(),name
        (dest/name).write_text(text);inputs[name]=str(path.relative_to(HERE.parent))
build=dest/'meson.build';text=build.read_text();at=text.index('\n',text.index("ipa_sources = files("))
text=text[:at+1]+''.join("    '"+n+"',\n" for n in inputs if n.endswith('.cpp'))+text[at+1:];build.write_text(text)
private=Path('/mnt/e/edk2-samurai-out/kernel422/integration-source')
for p in [tree/'include/linux/qcom-ipe-a5.h',tree/'src/ipa/camss-vfe/meson.build',dest/'meson.build']:
    if p.exists():shutil.copyfile(p,private/(p.parent.name+'-'+p.name))
report=dict(stage=422,source=str(tree),baseline_stage=421,common_libipa_numeric_sources=list(inputs),
    no_factory_coefficients_in_common_code=True,automatic_runtime_generation_integrated=False,
    kernel_unchanged=True,installed=False,passed=True)
(HERE/'candidate-source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
