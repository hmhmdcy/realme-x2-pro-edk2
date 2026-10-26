"""Include the new IPA in explicit options while retaining every old choice."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
for p in [HERE/'recipes/libcamera/APKBUILD',Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera316-r25/APKBUILD')]:
 s=p.read_text();needle='\t\t-Dpipelines=auto,virtual \\\n';assert s.count(needle)==1
 s=s.replace(needle,needle+'\t\t-Dipas=camss-vfe,ipu3,mali-c55,rkisp1,rpi/pisp,rpi/vc4,simple,vimc \\\n');p.write_text(s)
