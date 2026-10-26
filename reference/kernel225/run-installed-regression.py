from pathlib import Path
import subprocess,sys

here=Path(__file__).resolve().parent
for kind,width,height in [('raw',1928,1088),('rgb',2296,1728)]:
 subprocess.run([sys.executable,str(here/'run-installed-manual-case.py'),kind,str(width),str(height),'threaded'],check=True,timeout=170)
subprocess.run([sys.executable,str(here/'run-r13-lifecycle.py'),'system-threaded'],check=True,timeout=100)
