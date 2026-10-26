"""Inspect pinned IQ sources and retained target symbols without another full clone."""
from pathlib import Path
import importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s);s.mounted_build()
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';commit='9f17f1b568626b393e785b369c5dc94543774d7a'
tree=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',commit,'camx/src','chi-cdk/api'],text=True).splitlines()
matches=[x for x in tree if re.search(r'(ipe(cc13|gamma15|ltm13)|ipe_data|ipeStriping|ipeiq|cc13setting|gamma15setting|ltm13setting)',x,re.I)]
(P/'matching-source-paths-private.json').write_text(json.dumps(matches,indent=2)+'\n')
print(json.dumps(dict(pinned_commit=commit,paths=matches),indent=2))
elf=P.parent/'kernel352/CAMERA_ICP.elf-private'
symbols=subprocess.check_output(['arm-linux-gnueabi-objdump','-t','-C',str(elf)],text=True)
rows=[l for l in symbols.splitlines() if re.search(r'CC13|Gamma|GAMMA|ColorCorrect|COLOR_CORRECT|LTM|Ltm|IQSetting',l)]
(P/'firmware-iq-symbols-private.txt').write_text('\n'.join(rows)+'\n')
print('TARGET FIRMWARE IQ SYMBOLS\n'+'\n'.join(rows))
