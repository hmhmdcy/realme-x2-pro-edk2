from pathlib import Path
import hashlib,json,shutil,subprocess
import host
R=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');name='manager-hold276'
code=r'''
#include <libcamera/libcamera.h>
#include <iostream>
#include <string>
int main()
{
 libcamera::CameraManager manager;
 int ret=manager.start();
 if(ret)return 1;
 std::cout<<"{\"event\":\"ready\",\"cameras\":"<<manager.cameras().size()<<"}"<<std::endl;
 std::string command;
 if(!std::getline(std::cin,command) || command!="stop")return 2;
 manager.stop();
 std::cout<<"{\"event\":\"stopped\"}"<<std::endl;
 return 0;
}
'''
(R/(name+'.cpp')).write_text(code);p=SDK/'private'/(name+'.cpp');assert not p.exists();p.write_text(code)
prefix='/candidate275-r22';q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+prefix+'/usr/include/libcamera','/private/'+name+'.cpp','-L'+prefix+'/usr/lib','-Wl,-rpath-link,'+prefix+'/usr/lib','-lcamera','-lcamera-base','-o','/private/'+name],capture_output=True,timeout=90)
(host.PRIVATE/'manager-probe-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
target=host.PRIVATE/name;shutil.copyfile(SDK/'private'/name,target)
d=dict(stage=276,binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(code.encode()).hexdigest(),werror_clean=True,no_private_camera_lens_api_used=True)
(R/'manager-probe-build-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
