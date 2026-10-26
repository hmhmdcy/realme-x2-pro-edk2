"""Cross-check every IFE BLS mode with the retained factory parameter parser."""
from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel299/export-factory-bls.py').read_text()
source=source.replace("OLD=P.parent/'kernel298'","OLD=P.parent/'kernel298'")
source=source.replace("source=OLD/'sunny-imx319-tuning-private.bin'","source=P/'qtech-s5k3m5sx-tuning-private.bin'")
source=source.replace('9c8609ec7d2d0e70bbbc3809209fb446af26105892aa56a97a242f1b40775196',
 'a9059286f6acf1c5d76a1f943e9f62bf3358c019f1e0b419c24b073fec56da1b')
source=source.replace("previous=json.loads((OLD/'bls-typed-crosscheck-private.json').read_text());assert previous['original_reader_one_ife_root_18_regions_exact']",
 "previous=json.loads((HERE/'tele-bls-direct-validation.json').read_text());assert previous['ife_roots']==19 and previous['ife_regions']==152")
source=source.replace('parser-k299-bls-r3','parser-k306-tele-bls-r1')
source=source.replace("len(selected)==16","len(selected)==19")
source=source.replace("len(files)==16 and all(r['regions']==18", "len(files)==19 and all(r['regions']==8")
source=source.replace('stage=299','stage=306').replace('all16_ife_modes_exported=True','all19_ife_modes_exported=True')
source=source.replace('ife_regions=288','ife_regions=152')
source=source.replace("factory-bls-export-validation.json","tele-bls-export-validation.json")
source=source.replace("factory-bls-reader-private.log","tele-factory-bls-reader-private.log")
source=source.replace("factory-bls-export-private.json","tele-factory-bls-export-private.json")
exec(compile(source,'tele-factory-bls-export-generated.py','exec'),dict(__file__=str(HERE/'tele-factory-bls-export-generated.py')))
