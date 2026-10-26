"""Finite local environment/exec checks; synthetic NSS, real Linux UID transition."""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,shutil,stat,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel486')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def main():
    assert os.geteuid()==0
    storage=module(HERE.parent/'kernel461/storage.py','storage486_local');storage.mount.mounted_build()
    PRIVATE.mkdir(exist_ok=True);attempt=PRIVATE/('local-check-'+str(time.time_ns()));attempt.mkdir(mode=0o700)
    frozen=[HERE.parent/name for name in ['kernel449/user-launcher.py','kernel481/worker-body.py',
        'kernel481/prepare-runtime.py','kernel482/default-probe.py','kernel484/inspect-installed.py','kernel484/hardware-validation.json']]
    before={str(p.relative_to(HERE.parent)):sha(p) for p in frozen}
    launcher=module(HERE/'user-launcher.py','launcher486_local')
    ast.parse((HERE/'user-launcher.py').read_text())
    records=[];rejected=[]
    with tempfile.TemporaryDirectory(prefix='samurai-k486-') as folder:
        base=Path(folder);base.chmod(0o711)
        home=base/'personal-home';runtime=base/'runtime';outside=base/'owned-custom-config'
        for path in [home,runtime,outside]:path.mkdir(mode=0o700);os.chown(path,10000,10000)
        for name in ['.config/libcamera','custom-config/libcamera','.cache','custom-data','custom-state','custom-cache']:
            path=home/name;path.mkdir(parents=True)
        for path in home.rglob('*'):
            if path.is_dir():path.chmod(0o700);os.chown(path,10000,10000)
        marker=home/'.config/libcamera/configuration.yaml';marker.write_text('k486-local-home-sentinel\n');marker.chmod(0o600);os.chown(marker,10000,10000)
        stage=runtime/'k449-user-k486-local-r1';stage.mkdir(mode=0o700);os.chown(stage,10000,10000)
        program=stage/'environment-probe'
        program.write_text('''#!/usr/bin/python3
from pathlib import Path
import json,os,sys
keys=['HOME','USER','LOGNAME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_CACHE_HOME','XDG_STATE_HOME','XDG_RUNTIME_DIR','KEEP486','LIBCAMERA_LOG_LEVELS','XDG_CONFIG_DIRS']
caps=next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('CapEff:'))
print(json.dumps(dict(uid=os.getuid(),euid=os.geteuid(),gid=os.getgid(),groups=os.getgroups(),capeff=int(caps,16),cwd=os.getcwd(),argv=sys.argv,
 environment={key:os.environ.get(key) for key in keys},home_config=(Path(os.environ['HOME'])/'.config/libcamera/configuration.yaml').read_text())))
''')
        program.chmod(0o700);os.chown(program,10000,10000)
        launcher.RUNTIME_PARENT=runtime
        assert launcher.checked_program(str(stage),program.name)==(stage,program)
        alias=stage/'program-symlink';alias.symlink_to(program.name)
        wrong=stage/'root-owned-program';wrong.write_bytes(program.read_bytes());wrong.chmod(0o755)
        suid=stage/'setid-program';suid.write_bytes(program.read_bytes());os.chown(suid,10000,10000);suid.chmod(0o4700)
        for label,name in [('traversal','../environment-probe'),('absolute','/usr/bin/true'),('symlink',alias.name),('root-owned',wrong.name),('setid',suid.name)]:
            try:launcher.checked_program(str(stage),name)
            except (AssertionError,FileNotFoundError):rejected.append(label)
            else:raise AssertionError('Unsafe program accepted: '+label)
        arguments=['space argument','literal;$(not-a-shell)','--preserve=值']
        wrapper=attempt/'exec-contract-private.py'
        wrapper.write_text('''from pathlib import Path
import importlib.util,os,pwd,sys
spec=importlib.util.spec_from_file_location('launcher486_exec',__SOURCE_PATH__)
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
launcher.RUNTIME_PARENT=Path(__RUNTIME_PATH__)
account=pwd.struct_passwd(('k486-local-user','x',10000,10000,'local synthetic NSS',__ACCOUNT_HOME__,'/bin/false'))
def lookup(uid):
 assert uid==10000
 return account
def groups(name,gid):
 assert name==account.pw_name and gid==account.pw_gid
 os.setgroups([gid])
launcher.pwd.getpwuid=lookup;launcher.os.initgroups=groups
sys.argv=[__SOURCE_PATH__,__STAGE_PATH__,'environment-probe',*__ARGUMENTS__]
launcher.main()
'''.replace('__SOURCE_PATH__',repr(str(HERE/'user-launcher.py'))).replace('__RUNTIME_PATH__',repr(str(runtime))).replace('__ACCOUNT_HOME__',repr(str(home))).replace('__STAGE_PATH__',repr(str(stage))).replace('__ARGUMENTS__',repr(arguments)))
        common=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',LANG='C.UTF-8',HOME='/root',USER='root',LOGNAME='root',
                    KEEP486='preserved',LIBCAMERA_LOG_LEVELS='*:INFO',XDG_CONFIG_DIRS='/etc/xdg')
        cases={
            'root-inherited':dict(XDG_CONFIG_HOME='/root/.config',XDG_DATA_HOME='/root/.local/share',XDG_CACHE_HOME='/root/.cache',XDG_STATE_HOME='/root/.local/state',XDG_RUNTIME_DIR='/run/user/0'),
            'valid-user-settings':dict(XDG_CONFIG_HOME=str(home/'custom-config'),XDG_DATA_HOME=str(home/'custom-data'),XDG_CACHE_HOME=str(home/'custom-cache'),XDG_STATE_HOME=str(home/'custom-state'),XDG_RUNTIME_DIR=str(runtime)),
            'owned-external-and-relative':dict(XDG_CONFIG_HOME=str(outside),XDG_DATA_HOME='relative-data',XDG_CACHE_HOME='',XDG_STATE_HOME='/root/private-state',XDG_RUNTIME_DIR='relative-runtime')}
        for name,changes in cases.items():
            result=subprocess.run([sys.executable,'-B',str(wrapper)],env=dict(common,**changes),capture_output=True,timeout=15)
            (attempt/(name+'-stdout-private.json')).write_bytes(result.stdout);(attempt/(name+'-stderr-private.txt')).write_bytes(result.stderr)
            assert result.returncode==0 and result.stderr==b'',(name,result.returncode,result.stderr.decode())
            record=json.loads(result.stdout);environment=record['environment']
            assert record['uid']==record['euid']==record['gid']==10000 and record['capeff']==0 and record['groups']==[10000]
            assert record['cwd']==str(stage) and record['argv']==[str(program),*arguments]
            assert environment['HOME']==str(home) and environment['USER']==environment['LOGNAME']=='k486-local-user'
            assert environment['KEEP486']=='preserved' and environment['LIBCAMERA_LOG_LEVELS']=='*:INFO' and environment['XDG_CONFIG_DIRS']=='/etc/xdg'
            assert record['home_config']=='k486-local-home-sentinel\n'
            for key,suffix in launcher.XDG_HOME_DEFAULTS.items():
                expected=changes[key] if name=='valid-user-settings' or name=='owned-external-and-relative' and key=='XDG_CONFIG_HOME' else str(home/suffix)
                assert environment[key]==expected,(name,key,environment[key],expected)
            assert environment['XDG_RUNTIME_DIR']==str(runtime)
            records.append(dict(case=name,passed=True,actual_linux_uid=10000,capeff=0,argv_preserved=True,personal_home_sentinel_read=True,
                                stdout_sha256=sha(attempt/(name+'-stdout-private.json')),stderr_sha256=sha(attempt/(name+'-stderr-private.txt'))))
    assert before=={str(p.relative_to(HERE.parent)):sha(p) for p in frozen}
    report=dict(stage=486,passed=True,scope='finite local environment and exec contract only',
        account_lookup='synthetic local pwd entry and initgroups adapter; no host NSS/account changes',
        credentials_and_exec='real local Linux setgroups/setgid/setuid10000, CapEff0, chdir and execve',
        local_exec_cases=records,rejected_program_cases=rejected,home_user_logname_from_pwd=True,
        valid_personal_and_owned_external_xdg_preserved=True,inherited_root_relative_or_empty_xdg_replaced=True,
        unrelated_environment_preserved=True,libcamera_overrides_added=False,personal_home_configuration_sentinel_read=True,
        actual_libcamera_or_target_configuration_lookup_verified=False,target_actual_pwd_account_verified=False,
        target_warning_disappearance_verified=False,production_libraries_modified=False,no_ssh=True,no_usb=True,no_pm=True,no_sdk=True,
        selected_frozen_files_sha256=before,temporary_local_test_tree_removed=True,
        source_sha256={name:sha(HERE/name) for name in ['user-launcher.py','validate-local.py']},
        private_attempt=attempt.name)
    (attempt/'result-private.json').write_text(json.dumps(report,indent=2)+'\n')
    destination=HERE/'local-validation.json';assert not destination.exists(),'Preserve earlier receipt'
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(stage=486,passed=True,local_exec_cases=len(records),path_rejections=len(rejected),private_attempt=attempt.name)))


if __name__=='__main__':main()
