from pathlib import Path
import subprocess,os,signal,json,shutil
out=Path('/mnt/e/edk2-samurai-out/kernel117');work=Path('/home/cy122/x2pro-linux/parser-k117')
dest=work/'xml-imx471-traced';assert not dest.exists();dest.mkdir(mode=0o700);os.chown(dest,1000,1000)
trace=work/'decode-strace-private.txt'
env=dict(os.environ,LD_LIBRARY_PATH=str(work/'runtime/lib'))
args=['strace','-f','-tt','-o',str(trace),'stdbuf','-oL','-eL',str(work/'ParameterParser'),str(dest),'x',str(work/'xsd'),'-b'+str(work/'com.qti.sensormodule.sunny_imx471.bin')]
with (out/'imx471-traced-decode-private.log').open('wb') as log:
    p=subprocess.Popen(args,cwd=work,env=env,user=1000,group=1000,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    timed=False
    try: p.wait(timeout=8)
    except subprocess.TimeoutExpired:
        timed=True;os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=2)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=2)
if trace.exists():shutil.copyfile(trace,out/trace.name)
report=dict(bounded_trace_seconds=8,timed_out=timed,exit_code=p.returncode,process_group_terminated_and_waited=True,xml_files=len(list(dest.rglob('*.xml'))),goal_complete=False)
(out/'imx471-traced-decode-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
print((out/'imx471-traced-decode-private.log').read_text()[-3500:])
if trace.exists(): print('\n'.join(trace.read_text().splitlines()[-35:]))
