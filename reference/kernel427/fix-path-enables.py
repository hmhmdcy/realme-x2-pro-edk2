"""Apply DS4 local crop/round/clamp enables from the original node aggregator."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
k=m.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(k),*a],text=True)
assert git('rev-parse','HEAD').strip()==state['commit'] and not git('status','--porcelain') and json.loads((P/'intree-build-state.json').read_text())['terminal']
w={int(r['address'],16):int.from_bytes(bytes.fromhex(r['data']),'little') for r in json.loads((P/'module-enable-native-writes-private.json').read_text())}
assert w[0x4c]==0x5518 and w[0xd8c]==w[0xdac]==0xe00
p=k/'drivers/media/platform/qcom/camss/camss-vfe-175-ds4.c';text=p.read_text()
a='\tds4_update_bits(vfe, 0xdbc, 0x3f, 7);'
b=a+'\n\t/* The node aggregator owns local crop, round and clamp enables. */\n\tds4_update_bits(vfe, 0xd8c, 0xe00, 0xe00);\n\tds4_update_bits(vfe, 0xdac, 0xe00, 0xe00);'
assert text.count(a)==1;text=text.replace(a,b)
a='\tds4_update_bits(vfe, 0x4c, 0x5500, 0);';assert text.count(a)==1
text=text.replace(a,a+'\n\tds4_update_bits(vfe, 0xd8c, 0xe00, 0);\n\tds4_update_bits(vfe, 0xdac, 0xe00, 0);');p.write_text(text)
(HERE/'ds4-runtime.c').write_text(text[text.index('/* Runtime first-DS4 control'):])
subprocess.run(['git','-C',str(k),'add','--',str(p)],check=True);subprocess.run(['git','-C',str(k),'commit','-m','media: camss: configure DS4 local crop and depth enables'],check=True)
state['path_enables_fix_parent']=state['commit'];state['commit']=git('rev-parse','HEAD').strip();state['original_node_local_crop_round_clamp_enables_connected']=True
for row in state['source_hashes']:row['sha256']=hashlib.sha256((k/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'ds4-dma.patch').write_text(git('diff',state['parent_commit'],'HEAD'));print(json.dumps(dict(commit=state['commit'])))
