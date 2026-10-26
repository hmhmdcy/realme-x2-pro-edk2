from pathlib import Path
R=Path(__file__).resolve().parent
source=(R.parent/'kernel272/build-driver.py').read_text()
for before,after in [('kernel272','kernel274'),('camera272-build-r1','camera274-build-r1'),('stage=272','stage=274'),
 ('samurai-k272','samurai-k274'),("KBUILD_BUILD_VERSION='272'","KBUILD_BUILD_VERSION='274'"),
 ("'--module','VIDEO_S5KGW1',","'--module','VIDEO_S5KGW1','--module','VIDEO_LC898219XI',"),
 ('drivers/media/i2c/s5kgw1.o','drivers/media/i2c/lc898219xi.o'),
 ("'CONFIG_VIDEO_S5KGW1=m'","'CONFIG_VIDEO_LC898219XI=m'")]:
 assert before in source,before;source=source.replace(before,after)
exec(compile(source,'lens-build274-derived.py','exec'),dict(__file__=str(R/'build-lens-candidate.py')))
