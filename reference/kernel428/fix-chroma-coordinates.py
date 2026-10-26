"""Restore factory precrop with component coordinates for interleaved chroma."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
k=m.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(k),*a],text=True)
assert git('rev-parse','HEAD').strip()==state['commit'] and not git('status','--porcelain') and json.loads((P/'intree-build-state.json').read_text())['terminal']
rel='drivers/media/platform/qcom/camss/camss-vfe-175-ds4.c'
text=git('show',state['parent_commit']+':'+rel);old='\tds4_update_bits(vfe, 0xda8, 0x1fff1fff, full->width / 2 - 1);';assert text.count(old)==1
text=text.replace(old,'\t/* Chroma crop counts interleaved components, not CbCr pairs. */\n\tds4_update_bits(vfe, 0xda8, 0x1fff1fff, full->width - 1);');(k/rel).write_text(text)
subprocess.run(['git','-C',str(k),'add','--',rel],check=True);subprocess.run(['git','-C',str(k),'commit','-m','media: camss: use interleaved chroma coordinates for DS4 precrop'],check=True)
state['precrop_isolation_commit']=state['commit'];state['commit']=git('rev-parse','HEAD').strip();state['whole_frame_aligned_precrop_bypass_diagnostic']=False
state.update(original_precrop_enable_restored=True,chroma_crop_counts_interleaved_components=True,hardware_validated=False)
state['source_hashes']=[dict(path=rel,sha256=hashlib.sha256((k/rel).read_bytes()).hexdigest())]
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'precrop-chroma.patch').write_text(git('diff',state['parent_commit'],'HEAD'))
text=(HERE.parent/'kernel427/check-runtime.py').read_text().replace('stage=427','stage=428').replace("HERE.parent/'kernel426/ds4-model.py'","HERE/'native-geometry.py'")
text=text.replace('native_precrop_ds4_depth_and_r2pd_match=True','native_full_crop_to_precrop_geometry_production_executed=True,native_precrop_ds4_depth_and_r2pd_match=True,interleaved_chroma_crop_coordinates_match=True,original_precrop_enable_restored=True')
(HERE/'check-runtime.py').write_text(text);(HERE/'runtime-contract.c').write_text((HERE.parent/'kernel427/runtime-contract.c').read_text())
print(json.dumps(dict(commit=state['commit'],precrop_enabled=True,chroma_width='full output component width')))
