from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
kernel=m.mounted_build().parent/'source354';camss=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True)
base='faf093770826a3bbe4b6f21f3b93303c62591627';assert git('rev-parse','HEAD').strip()==base and not git('status','--porcelain')
for p in [kernel,*(kernel.parents)]:assert not (p/'AGENTS.md').exists(),str(p/'AGENTS.md')
subprocess.run(['git','-C',str(kernel),'switch','-c','samurai-vfe175-ds4-codec426'],capture_output=True,check=True)
names=['camss-vfe-175-ds4.c','camss-vfe-175-ds4.h','Makefile'];before={n:(kernel/camss/n).read_text() if (kernel/camss/n).exists() else '' for n in names}
for n in names[:2]:(kernel/camss/n).write_bytes((HERE/n).read_bytes())
text=before['Makefile'];needle='camss-vfe-175-mnds.o';assert text.count(needle)==1
(kernel/camss/'Makefile').write_text(text.replace(needle,needle+' \\\n\t\tcamss-vfe-175-ds4.o'))
subprocess.run(['git','-C',str(kernel),'diff','--check'],check=True)
subprocess.run(['git','-C',str(kernel),'add','--',*[str(camss/n) for n in names]],check=True)
patch=git('diff','--cached','--binary');(HERE/'ds4-register-codec.patch').write_text(patch)
subprocess.run(['git','-C',str(kernel),'commit','-m','media: camss: compose calibrated VFE175 DS4 and PD10 registers'],check=True)
rows=[dict(path=str(camss/n),sha256=hashlib.sha256((kernel/camss/n).read_bytes()).hexdigest()) for n in names]
r=dict(stage=426,parent_commit=base,commit=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),source_hashes=rows,
 ds4_register_composition_implemented=True,ds4_runtime_producer_not_connected=True,ds4_dma_and_format_registration_not_implemented=True,
 no_new_user_api=True,no_board_or_sensor_change=True,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
