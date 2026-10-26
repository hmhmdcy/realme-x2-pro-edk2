"""Exercise DC/IP ordering across four requests without restarting IPE."""
from pathlib import Path
import ast,hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
text=(HERE/'pd10-ipe.c').read_text()
text=text.replace('b.sequence==0','b.sequence==mode')
a=text.index('\tfor(unsigned mode=0;mode<4;mode++) {');z=text.index('\t\tread_exact(directory,"full-private.bin"',a)
text=text[:a]+'''\tint fd=open(argv[1],O_RDWR|O_NONBLOCK|O_CLOEXEC);assert(fd>=0);
\tint media=open(argv[2],O_RDWR|O_CLOEXEC);assert(media>=0);
\tformat(fd,out_type);format(fd,cap_type);
\tstruct memory input[2],output[1];allocate(fd,out_type,input);allocate(fd,cap_type,output);
\tfor(unsigned mode=0;mode<4;mode++) {
'''+text[z:]
text=text.replace('unsigned type=cap_type;call(fd,VIDIOC_STREAMON,&type);type=out_type;call(fd,VIDIOC_STREAMON,&type);','if(!mode) { unsigned type=cap_type;call(fd,VIDIOC_STREAMON,&type);type=out_type;call(fd,VIDIOC_STREAMON,&type); }')
text=text.replace('assert(header[0]==1 && header[1]==46128)','assert(header[0]==mode+1 && header[1]==46128)')
a=text.index('\t\ttype=out_type;call(fd,VIDIOC_STREAMOFF');z=text.index('\tfree(data);',a)
text=text[:a]+'''\t\tstruct pollfd done={.fd=request,.events=POLLPRI};
\t\tassert(poll(&done,1,3000)==1 && (done.revents&POLLPRI) && !(done.revents&(POLLERR|POLLHUP|POLLNVAL)));
\t\tassert(!close(request));
\t}
\tunsigned type=out_type;call(fd,VIDIOC_STREAMOFF,&type);type=cap_type;call(fd,VIDIOC_STREAMOFF,&type);
\tfor(unsigned i=0;i<2;i++)assert(!munmap(input[i].p,input[i].bytes));
\tassert(!munmap(output[0].p,output[0].bytes));assert(!close(media) && !close(fd));
'''+text[z:]
(HERE/'warm-ipe.c').write_text(text)
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-I'+str(P/'includes'),str(HERE/'warm-ipe.c'),'-o',str(P/'warm-ipe')],capture_output=True)
(P/'warm-client-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
r=dict(stage=430,static_arm64=True,werror=True,source_sha256=hashlib.sha256(text.encode()).hexdigest(),probe_sha256=hashlib.sha256((P/'warm-ipe').read_bytes()).hexdigest(),single_open_stream_session=True,same_fresh_sof_pair_from_attempt='r2',passed=True)
(HERE/'warm-client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n')
prepare=(HERE/'prepare-runtime.py').read_text().replace('client-build-validation.json','warm-client-build-validation.json').replace("HERE/'pd10-ipe.c'","HERE/'warm-ipe.c'").replace("P/'pd10-ipe'","P/'warm-ipe'")
prepare=prepare.replace("for name in ['full-private.bin','pd10-private.bin','parameters-private.bin']:files[name]=P/name","for name in ['full-private.bin','pd10-private.bin','parameters-private.bin']:files[name]=P/'runtime-collected-r2/replay'/name")
prepare=prepare.replace("state['live_sensor_capture']=False","state['live_sensor_capture']=False;state['fresh_pair_origin']='430 r2 main SOF5';state['persistent_ipe_session']=True\n assert s['starts']==s['stops']==1")
ast.parse(prepare);(HERE/'prepare-warm-runtime.py').write_text(prepare)
print(json.dumps(r))
