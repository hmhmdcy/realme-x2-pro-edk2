"""Read the three required files from the retained pinned Git revision."""
from pathlib import Path
import subprocess
import host
paths=['chi-cdk/api/chromatix/XSD/isp/ltm_1_3_0.xsd','chi-cdk/api/chromatix/XSD/isp/cc_1_3_0.xsd','camx/src/hwl/titan17x/camxtitan17xsettings.xml']
directory=host.PRIVATE/'sources';directory.mkdir(exist_ok=True)
for name in paths:
 target=directory/Path(name).name
 if not target.exists():target.write_bytes(subprocess.check_output(['git','-C','/home/cy122/x2pro-linux/refs/CamxChi-k117','show','9f17f1b568626b393e785b369c5dc94543774d7a:'+name],timeout=30))
print('Retained three fixed-revision source files; factory tuning and sources remain private.')
