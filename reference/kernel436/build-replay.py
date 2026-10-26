from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
storage.mount.mounted_build()
source=(HERE.parent/'kernel430/pd10-ipe.c').read_text()
source=source.replace('for(unsigned mode=0;mode<4;mode++) {','const struct qcom_ipe_a5_frame_params stock=params;\n\tfor(unsigned mode=0;mode<5;mode++) {\n\t\tparams=stock;\n\t\tif(mode==1 || mode==2) {params.flags&=~QCOM_IPE_A5_LTM;memset(&params.ltm,0,sizeof(params.ltm));}\n\t\tif(mode==2) {params.flags=0;memset(&params.gamma,0,sizeof(params.gamma));}\n\t\tif(mode==3) memset(&params,0,sizeof(params));')
a=source.index('\t\tif(mode==1 || mode==2)for(');z=source.index('\n\t\tuint64_t full_hash',a);source=source[:a]+source[z:]
a=source.index('static unsigned scratch(');z=source.index('\nint main(',a);source=source[:a]+source[z:]
source=source.replace('\tunsigned char *data=malloc(0x40000+16);assert(data);\n','')
a=source.index('\t\tunsigned bytes=scratch(');z=source.index('\n\t\ttype=out_type;',a)
source=source[:a]+'''        save(directory,mode,"output-private",output[0].p,460800);
        printf("REPLAY_FRAME mode=%u flags=%u full=%016llx pd10=%016llx output=%016llx\\n",mode,params.flags,(unsigned long long)full_hash,(unsigned long long)coarse_hash,(unsigned long long)hash(output[0].p,460800));fflush(stdout);
        struct pollfd done={.fd=request,.events=POLLPRI};
        assert(poll(&done,1,3000)==1 && (done.revents&POLLPRI) && !(done.revents&(POLLERR|POLLHUP|POLLNVAL)));
'''+source[z:]
source=source.replace('free(data);puts("PD10_IPE_RESULT result=0 frames=4")','puts("TONE_REPLAY_RESULT result=0 frames=5")')
(HERE/'tone-replay.c').write_text(source)
inc=P/'replay-includes/linux';inc.mkdir(parents=True,exist_ok=True)
shutil.copyfile(P.parent/'kernel430/includes/linux/qcom-ipe-a5.h',inc/'qcom-ipe-a5.h')
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-I'+str(inc.parent),str(HERE/'tone-replay.c'),'-o',str(P/'tone-replay')],capture_output=True)
(P/'replay-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
live=json.loads((HERE/'runtime-r1-validation.json').read_text());assert live['state']['passed']
sof=live['state']['captures']['scene-native']['trace']['sof'];case=P/'runtime-collected-r1/scene-native'
for old,new in [(f'tone-{sof}-full.nv12','full-private.bin'),(f'tone-{sof}-coarse.pd10','pd10-private.bin'),(f'tone-{sof}-params.bin','parameters-private.bin')]:shutil.copyfile(case/old,P/new)
r=dict(stage=436,static_arm64=True,werror=True,source_sha256=hashlib.sha256((HERE/'tone-replay.c').read_bytes()).hexdigest(),probe_sha256=hashlib.sha256((P/'tone-replay').read_bytes()).hexdigest(),same_frame_source_sof=sof,modes=['stock','LTM off','colour only','bypass','repeat stock'],no_source_pixel_changes=True,passed=True)
(HERE/'replay-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
