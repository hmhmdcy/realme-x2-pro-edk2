from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
state=json.loads((HERE/'proposal-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');mount=importlib.util.module_from_spec(spec);spec.loader.exec_module(mount)
build=mount.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['parent'] and not git('status','--porcelain')
for leaf in state['changed']:
 p=source/relative/leaf;prior=(P/(leaf+'.before')).read_bytes();assert p.read_bytes()==prior if p.exists() else not prior
git('switch','-c','samurai-ipe-direct-dma388')
for leaf in state['changed']:(source/relative/leaf).write_bytes((P/(leaf+'.proposed')).read_bytes())
git('diff','--check');git('add','--',*[str(relative/n) for n in state['changed']]);git('commit','-m','media: camss: import IPE images through DMA-BUF and DMA-SG queues')
state.update(commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),source=str(source),applied=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
script=(HERE.parent/'kernel387/build-intree.py').read_text().replace('stage=387','stage=388')
script=script.replace("'videobuf2-memops','videobuf2-vmalloc'","'videobuf2-memops','videobuf2-vmalloc','videobuf2-dma-sg'")
assert 'videobuf2-dma-sg' in script
(HERE/'build-intree.py').write_text(script);shutil.copyfile(P.parent/'kernel387/live-overlay-state-private.json',P/'live-overlay-state-private.json')
print(json.dumps(state,indent=2))
