"""Build the sensor/dependency closure and restore the shared kernel output."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,stat,subprocess,time
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE=Path('/home/cy122/x2pro-linux/camera325-gw1-tpg-kernel')
spec=importlib.util.spec_from_file_location('storage',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
BUILD=storage.mounted_build();source=TREE/'drivers/media/i2c/s5kgw1.c'
expected=json.loads((HERE/'kernel-source-validation.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==expected['source_sha256']
release=(BUILD/'include/config/kernel.release').read_text().strip();assert release=='7.3.0-rc6-rmx1931-samurai-k298+'
symbols={line.split()[1]:line.split()[2] for line in (BUILD/'Module.symvers').read_text().splitlines()}
modules={'drivers/media/i2c/s5kgw1'};pending=list(modules)
while pending:
 name=pending.pop();output=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(BUILD/(name+'.ko'))],text=True)
 for line in output.splitlines():
  module=symbols.get(line.split()[-1])
  if module and module!='vmlinux' and module not in modules:modules.add(module);pending.append(module)
prefixes={}
for name in modules:prefixes.setdefault(str(Path(name).parent),[]).extend([Path(name).name,'.'+Path(name).name])
def outputs():return {p for directory,starts in prefixes.items() for p in (BUILD/directory).iterdir() if p.is_file() and p.name.startswith(tuple(starts))}
names=['.config','.config.old','Module.symvers','modules.order','Makefile','source','include/generated/compile.h','include/generated/utsversion.h','include/generated/utsrelease.h',
 'include/generated/autoconf.h','include/config/auto.conf','include/config/auto.conf.cmd','include/config/kernel.release']
for directory in prefixes:names += [directory+'/modules.order',directory+'/Module.symvers']
saved={}
for path in outputs()|{BUILD/n for n in names}:
 key=str(path.relative_to(BUILD))
 if path.is_symlink():saved[key]=('symlink',os.readlink(path),0)
 elif path.is_file():saved[key]=('file',path.read_bytes(),stat.S_IMODE(path.stat().st_mode))
 else:saved[key]=('missing',None,0)
attempt=1
while (P/f'build-r{attempt}.log').exists():attempt+=1
backup=P/f'build-r{attempt}-before';backup.mkdir()
for name,(kind,data,mode) in saved.items():
 if kind=='file':p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(mode)
(backup/'metadata.json').write_text(json.dumps({n:dict(kind=v[0],mode=v[2],target=v[1] if v[0]=='symlink' else None) for n,v in saved.items()},indent=2)+'\n')
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='298',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',TMPDIR=str(BUILD.parent/'tmp'))
command=['make','-C',str(TREE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j3','W=1','KCFLAGS=-Werror','KERNELRELEASE='+release,*[name+'.ko' for name in sorted(modules)]]
log=P/f'build-r{attempt}.log';start=time.monotonic();code=None;target=P/f's5kgw1-tpg325-r{attempt}.ko';state=P/'build-state.json'
try:
 with log.open('xb') as output:
  child=subprocess.Popen(command,env=env,stdout=output,stderr=subprocess.STDOUT)
  state.write_text(json.dumps(dict(pid=child.pid,terminal=False,attempt=attempt))+'\n');code=child.wait()
 if code==0:shutil.copyfile(BUILD/'drivers/media/i2c/s5kgw1.ko',target)
finally:
 for path in outputs():
  if str(path.relative_to(BUILD)) not in saved:path.unlink()
 for name,(kind,data,mode) in saved.items():
  p=BUILD/name
  if p.is_symlink():p.unlink()
  if kind=='symlink':
   if p.exists():p.unlink()
   p.symlink_to(data)
  elif kind=='file':p.write_bytes(data);p.chmod(mode)
  elif p.exists():p.unlink()
 state.write_text(json.dumps(dict(pid=child.pid,terminal=True,attempt=attempt,exit_code=code,build_outputs_restored=True))+'\n')
diagnostics=[line for line in log.read_text(errors='replace').splitlines() if 'warning:' in line.lower() or 'error:' in line.lower()]
report=dict(stage=325,attempt=attempt,exit_code=code,seconds=round(time.monotonic()-start,2),diagnostics=diagnostics,kernel_release=release,
 only_sensor_module_target_and_dependency_closure=True,dependency_modules=sorted(modules-{'drivers/media/i2c/s5kgw1'}),build_outputs_restored=True,installed=False)
if code==0:
 info=lambda field:subprocess.check_output(['modinfo','-F',field,str(target)],text=True).strip()
 imports={line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True).splitlines()}
 assert imports<=symbols.keys() and info('intree')=='Y'
 report.update(module=str(target),module_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),module_bytes=target.stat().st_size,intree=True,vermagic=info('vermagic'),imports_available=True)
report['passed']=code==0 and not diagnostics
(HERE/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
