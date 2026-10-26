"""Copy the current published318 sources and refresh the cumulative diff."""
from pathlib import Path
import shutil,subprocess
HERE=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera318-lsc-kernel')
subdir=Path('drivers/media/platform/qcom/camss')
for source in (HERE/'kernel').iterdir():
 if source.is_file():
  relative=Path('include/uapi/linux')/source.name if source.name=='qcom-camss-config.h' else subdir/source.name
  shutil.copyfile(source,TREE/relative)
(HERE/'lsc-driver.patch').write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff','HEAD']))
print('Refreshed318 kernel source and patch.')
