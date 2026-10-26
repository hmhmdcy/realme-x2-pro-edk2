from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'frame-abi-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';relative=Path('drivers/media/platform/qcom/camss');git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent='6b8e3b1a28ff9ea60391045b03b746499d1d9400';assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
name='Makefile';before=(source/relative/name).read_text();anchor='camss-icp-a5-boot.o';assert before.count(anchor)==1
after=before.replace(anchor,anchor+' camss-icp-a5-ipe.o');(P/(name+'.before')).write_text(before);(P/(name+'.proposed')).write_text(after)
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+str(relative/name),tofile='b/'+str(relative/name)))
for name in ['camss-icp-a5-ipe.c','camss-icp-a5-ipe.h']:
 assert not (source/relative/name).exists();text=(HERE/name).read_text();(P/(name+'.proposed')).write_text(text)
 patch+=''.join(difflib.unified_diff([],text.splitlines(True),fromfile='/dev/null',tofile='b/'+str(relative/name)))
(HERE/'ipe-frame-builder.patch').write_text(patch)
for name in ['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c']:(P/(name+'.proposed')).write_bytes((source/relative/name).read_bytes())
(P/'live-overlay-state-private.json').write_bytes((P.parent/'kernel379/live-overlay-state-private.json').read_bytes())
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=380,parent=parent,changed=['Makefile','camss-icp-a5-ipe.c','camss-icp-a5-ipe.h'],frame_submission_implemented=False,installed=False),indent=2)+'\n')
print('Prepared independent kernel frame builder; no frame submit, DT or userspace mutation.')
