from pathlib import Path
import importlib.util,subprocess
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('storage434reopen',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);K=m.mounted_build().parent/'source354'
for name,ranges in {'camss-vfe-17x.c':[(150,235)],'camss-vfe-175-pixel.c':[(250,280)],'camss-vfe.c':[(990,1140),(1250,1410)]}.items():
 p=K/'drivers/media/platform/qcom/camss'/name;lines=p.read_text().splitlines()
 print('\nFILE',name)
 for start,end in ranges:
  for i in range(start-1,min(end,len(lines))):print(f'{i+1}: {lines[i]}')
print(subprocess.check_output(['git','-C',str(K),'grep','-n','-E','vfe_params_apply_queued|vfe_params_apply_next|reg_update =|ds4_configured','--','drivers/media/platform/qcom/camss'],text=True))
