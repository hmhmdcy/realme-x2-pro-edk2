"""Build a persistent request test for bypass/DC/bypass/DC session transitions."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
t=(HERE.parent/'kernel430/warm-ipe.c').read_text();a=t.index('\t\tif(mode==1 || mode==2)');z=t.index('\n\t\tuint64_t full_hash',a);t=t[:a]+t[z:]
t=t.replace('\tfor(unsigned mode=0;mode<4;mode++) {','\tconst struct qcom_ipe_a5_frame_params stock=params;\n\tfor(unsigned mode=0;mode<4;mode++) {\n        params=(mode==0 || mode==2)?(struct qcom_ipe_a5_frame_params){0}:stock;')
a=t.index('\t\tunsigned bytes=scratch(');z=t.index('\t\tstruct pollfd done=',a)
t=t[:a]+'''        uint32_t header[4]={};
        if(mode==1 || mode==3) {
            unsigned bytes=scratch(data,0x40000+16);save(directory,mode,"scratch-private",data,bytes);
            memcpy(header,data,16);assert(header[0]==mode+1 && header[1]==46128);
        }
        save(directory,mode,"output-private",output[0].p,460800);
        printf("{\\"mode\\":%u,\\"dc\\":%u,\\"full_hash\\":\\"%016llx\\",\\"pd10_hash\\":\\"%016llx\\",\\"output_hash\\":\\"%016llx\\",\\"passed\\":true}\\n",mode,mode%2,(unsigned long long)full_hash,(unsigned long long)coarse_hash,(unsigned long long)hash(output[0].p,460800));fflush(stdout);
'''+t[z:]
(HERE/'transition-ipe.c').write_text(t)
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-I'+str(P.parent/'kernel430/includes'),str(HERE/'transition-ipe.c'),'-o',str(P/'transition-ipe')],capture_output=True)
(P/'transition-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
r=dict(stage=431,source_sha256=hashlib.sha256(t.encode()).hexdigest(),probe_sha256=hashlib.sha256((P/'transition-ipe').read_bytes()).hexdigest(),static_arm64_werror=True,four_requests_one_stream=True,sequence=['bypass','DC','bypass','DC'],passed=True)
(HERE/'transition-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
