"""Reuse322's temporary installed-IPA probe for the telephoto sensor."""
from pathlib import Path
here=Path(__file__).resolve().parent
s=(here.parent/'kernel322/prepare-runtime.py').read_text()
s=s.replace(".replace('stage=321','stage=322')",".replace('stage=321','stage=323')")
s=s.replace("(HERE/'native-probe.py').write_text(s)","s=s.replace(\"startswith('imx319 ')\",\"startswith('s5k3m5 ')\").replace(\"'imx319',sensor\",\"'s5k3m5',sensor\").replace('IMX319 node','S5K3M5 node')\n(HERE/'native-probe.py').write_text(s)")
s=s.replace('k322-lsc-','k323-lsc-')
exec(compile(s,str(here/'prepare-runtime.py'),'exec'),dict(__file__=str(here/'prepare-runtime.py'),__name__='__main__'))
