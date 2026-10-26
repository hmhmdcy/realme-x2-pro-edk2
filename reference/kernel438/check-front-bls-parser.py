from pathlib import Path
import storage
HERE=Path(__file__).resolve().parent;work=storage.mount.mounted_build().parent/'parser438-front-bls'
source=(HERE.parent/'kernel299/export-factory-bls.py').read_text()
source=source.replace("source=OLD/'sunny-imx319-tuning-private.bin'", "source=P.parent/'kernel324/sunny_imx471-tuning-private.bin'")
source=source.replace('9c8609ec7d2d0e70bbbc3809209fb446af26105892aa56a97a242f1b40775196','f07e6e6ce99ce2fdff54703f87c8f00be18b719d992b37591cec91d090e1928e')
source=source.replace("previous=json.loads((OLD/'bls-typed-crosscheck-private.json').read_text());assert previous['original_reader_one_ife_root_18_regions_exact']", "previous=json.loads((HERE/'sunny_imx471-bls-direct-validation.json').read_text());assert previous['ife_roots']==1 and previous['ife_regions']==5")
source=source.replace("Path('/home/cy122/x2pro-linux/parser-k299-bls-r3')",repr(work).replace('PosixPath','Path'))
source=source.replace('len(selected)==16','len(selected)==1').replace("len(files)==16 and all(r['regions']==18", "len(files)==1 and all(r['regions']==5")
source=source.replace('stage=299','stage=438').replace('all16_ife_modes_exported=True','all1_ife_modes_exported=True').replace('ife_regions=288','ife_regions=5').replace('factory-bls-','front-factory-bls-')
exec(compile(source,str(HERE/'front-bls-parser-generated.py'),'exec'))
