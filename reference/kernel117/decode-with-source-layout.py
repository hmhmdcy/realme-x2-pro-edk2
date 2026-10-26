from pathlib import Path
import subprocess,os,signal,json,shutil,resource
out=Path('/mnt/e/edk2-samurai-out/kernel117');work=Path('/home/cy122/x2pro-linux/parser-k117')
schema=work/'api/sensor';schema.mkdir(parents=True,mode=0o700)
for p in [schema.parent,schema]:os.chown(p,1000,1000)
for source in (out/'CamxChi/chi-cdk/api/sensor').glob('*.xsd'):
    dest=schema/source.name;shutil.copyfile(source,dest);os.chown(dest,1000,1000)
dest=work/'xml-imx471-layout';dest.mkdir(mode=0o700);os.chown(dest,1000,1000)
env=dict(os.environ,LD_LIBRARY_PATH=str(work/'runtime/lib'))
args=['stdbuf','-oL','-eL',str(work/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(work/'com.qti.sensormodule.sunny_imx471.bin')]
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(8,8))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024*1024,32*1024*1024))
with (out/'imx471-source-layout-decode-private.log').open('wb') as log:
    p=subprocess.Popen(args,cwd=work,env=env,user=1000,group=1000,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
    timed=False
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        timed=True;os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=2)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=2)
report=dict(source_relative_include_layout_correct=True,exit_code=p.returncode,timed_out=timed,xml_files=len(list(dest.rglob('*.xml'))),max_memory_mib=256,bounded_cpu_seconds=8,process_group_waited=True,goal_complete=False)
(out/'imx471-source-layout-decode-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));print((out/'imx471-source-layout-decode-private.log').read_text()[-4200:])
