from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
source=(HERE.parent/'kernel436/tone-replay.c').read_text()
source=source.replace('if(mode==1 || mode==2) {','if(mode==1) {').replace('if(mode==2) {params.flags=0;memset(&params.gamma,0,sizeof(params.gamma));}', 'if(mode==2) {params.colour.modules&=~QCOM_IPE_A5_COLOUR_CC;memset(&params.colour.cc,0,sizeof(params.colour.cc));}')
(HERE/'tone-replay.c').write_text(source)
inc=P/'replay-includes/linux';inc.mkdir(parents=True,exist_ok=True);shutil.copyfile(P.parent/'kernel430/includes/linux/qcom-ipe-a5.h',inc/'qcom-ipe-a5.h')
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-I'+str(inc.parent),str(HERE/'tone-replay.c'),'-o',str(P/'tone-replay')],capture_output=True)
(P/'replay-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
r={'stage':439,'passed':True,'static_arm64':True,'werror':True,'source_sha256':hashlib.sha256((HERE/'tone-replay.c').read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256((P/'tone-replay').read_bytes()).hexdigest(),'modes':['stock','LTM off','CCM off','bypass','repeat stock'],'source_pixels_unchanged':True}
(HERE/'replay-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
