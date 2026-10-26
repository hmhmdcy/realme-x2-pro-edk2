from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True)
assert git('rev-parse','HEAD').strip()==state['commit'] and not git('status','--porcelain') and json.loads((P/'intree-build-state.json').read_text())['terminal']
path=kernel/'drivers/media/platform/qcom/camss/camss-vfe-175-ds4.c';text=path.read_text();start=text.index('/* Runtime first-DS4 control')
old=text[start:];new=(HERE/'ds4-runtime.c').read_text();assert old!=new
assert old.replace('\tu32 value;\n\n\t/* The caller validated geometry and queued addresses before enabling. */','\tstruct camss_pd10_layout layout;\n\tu32 value;\n\n\t/* The caller validated geometry and queued addresses before enabling. */\n\tif (WARN_ON(camss_format_pd10_layout(pix->width, pix->height, &layout)))\n\t\treturn;').replace('writel_relaxed(stride * height, vfe->base + 0x2758);','writel_relaxed(layout.bytes, vfe->base + 0x2758);')==new
path.write_text(text[:start]+new)
subprocess.run(['git','-C',str(kernel),'add','--',str(path)],check=True);subprocess.run(['git','-C',str(kernel),'commit','-m','media: camss: use padded PD10 slice for WM frame increment'],check=True)
state['frame_increment_fix_parent']=state['commit'];state['commit']=git('rev-parse','HEAD').strip();state['pd10_frame_increment_uses_padded_slice']=True
for row in state['source_hashes']:row['sha256']=hashlib.sha256((kernel/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'ds4-dma.patch').write_text(git('diff',state['parent_commit'],'HEAD'))
print(json.dumps(dict(commit=state['commit'],padded_frame_increment=True)))
