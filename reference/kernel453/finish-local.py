from pathlib import Path
import storage
storage.mount.mounted_build()
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel441/finish-local.py').read_text().replace('stage=441','stage=453')
exec(compile(source,str(HERE/'finish-local.py'),'exec'))
