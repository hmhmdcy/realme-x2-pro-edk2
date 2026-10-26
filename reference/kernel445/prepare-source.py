"""Optimize exact grid arithmetic and expose the focus memory/CPU phases."""
from pathlib import Path
import difflib,hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;v=storage.mount.mounted_build().parent
old=v/'libcamera444-focused-ipe';new=storage.candidate();assert old.is_dir() and not new.exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[s for s in n if s=='pkg' or s.startswith('pkg-before') or s=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';header='src/libcamera/pipeline/camss-vfe/hardware_focus.h';pipeline='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
before={name:(tree/name).read_text() for name in [header,pipeline]}
shutil.copyfile(HERE/'hardware_focus.h',tree/header)
a='const auto score=measureFrameFocus(buffer,focusConfig);'
b='''FocusMeasurementTiming focusTiming;
  const auto score=measureFrameFocus(buffer,focusConfig,&focusTiming);
  LOG(CamssVfe,Debug)<<"FOCUS_TIMING epoch="<<frameEpoch<<" sof="<<sequence
   <<" sync-start-us="<<focusTiming.syncStartUs<<" map-us="<<focusTiming.mapUs
   <<" sample-us="<<focusTiming.sampleUs<<" score-us="<<focusTiming.scoreUs
   <<" unmap-us="<<focusTiming.unmapUs<<" sync-end-us="<<focusTiming.syncEndUs;'''
assert before[pipeline].count(a)==1;(tree/pipeline).write_text(before[pipeline].replace(a,b))
(HERE/'0057-camss-exact-focus-grid.patch').write_text(''.join(''.join(difflib.unified_diff(before[n].splitlines(True),(tree/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n in [header,pipeline]))
state=json.loads((HERE.parent/'kernel444/source-state.json').read_text());names={r['path'] for r in state['source_hashes']}|{header}
state['source_hashes']=[dict(path=n,sha256=hashlib.sha256((tree/n).read_bytes()).hexdigest()) for n in sorted(names)]
state.update(stage=445,source=str(tree),baseline_stage=444,source_baseline_stage=444,changed_this_stage=[header,pipeline],build_pending=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=445,source=str(tree),private_ipa_version=6,changed_production_files=2,phone_changed=False,passed=True)))
