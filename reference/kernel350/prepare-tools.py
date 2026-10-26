"""Reuse the checked Gamma decoder with the actual IPE schema and E storage."""
from pathlib import Path
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel347/decode-gamma.py').read_text()
s=s.replace('complete IFE Gamma','complete IPE Gamma').replace('gamma16_ife','gamma15_ipe').replace('gamma16','gamma15')
s=s.replace('count*272','count*1040').replace('range(0,len(data),272)','range(0,len(data),1040)').replace('<65f','<257f').replace('samples_per_curve=65','samples_per_curve=257')
s=s.replace('gamma_1_6_0.xsd','gamma_1_5_0.xsd').replace('stage=347','stage=350').replace('all_retained_ife_gamma','all_retained_ipe_gamma')
s=s.replace('HERE=Path(__file__).resolve().parent;P=host.PRIVATE','''HERE=Path(__file__).resolve().parent;P=host.PRIVATE
import importlib.util
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
WORK=storage.mounted_build().parent/'parser350';WORK.mkdir(mode=0o755,exist_ok=True)''')
s=s.replace("Path('/home/cy122/x2pro-linux')/('parser-k347-'+name+'-gamma-r1')","WORK/(name+'-gamma-r1')")
(HERE/'decode-gamma.py').write_text(s)
print('Prepared IPE Gamma15 decoder:257-point/channel1040, full tree, OEM XML cross-check, E-drive work directories.')
