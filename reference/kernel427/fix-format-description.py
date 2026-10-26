"""Describe the local PD10 FourCC without changing the shared V4L2 core."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
kernel=m.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True)
assert git('rev-parse','HEAD').strip()==state['commit'] and not git('status','--porcelain')
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
path=kernel/'drivers/media/platform/qcom/camss/camss-video.c';text=path.read_text()
old='\tf->pixelformat = video->formats[i].pixelformat;\n'
assert text.count(old)==1
text=text.replace(old,old+'\tif (f->pixelformat == V4L2_PIX_FMT_QCOM_PD10_LOCAL)\n\t\tstrscpy(f->description, "Qualcomm PD10 (local)",\n\t\t\tsizeof(f->description));\n')
path.write_text(text)
subprocess.run(['git','-C',str(kernel),'add','--',str(path)],check=True)
subprocess.run(['git','-C',str(kernel),'commit','-m','media: camss: describe the experimental PD10 capture format'],check=True)
state['format_description_fix_parent']=state['commit'];state['commit']=git('rev-parse','HEAD').strip()
for row in state['source_hashes']:row['sha256']=hashlib.sha256((kernel/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'ds4-dma.patch').write_text(git('diff',state['parent_commit'],'HEAD'))
print(json.dumps(dict(commit=state['commit'],local_format_description=True)))
