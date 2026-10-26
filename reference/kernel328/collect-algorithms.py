"""Reuse the read-only vendor collector for the exact AWB/AEC components."""
from pathlib import Path
import host

HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel316/collect-oem-hal.py').read_text()
s=s.replace('k316-oem-hal','k328-oem-stats').replace('hal-source','stats-source')
s=s.replace("candidates=[mount/'lib64/hw/camera.qcom.so',*sorted((mount/'lib64').glob('libcamx*.so'))]",
 "candidates=[mount/('lib64/camera/components/'+name) for name in ['com.qti.stats.awb.so','com.qti.stats.awbwrapper.so','com.qti.stats.aec.so']]")
exec(compile(s,str(HERE/'collect-algorithms.py'),'exec'),dict(__file__=str(HERE/'collect-algorithms.py'),__name__='__main__'))
