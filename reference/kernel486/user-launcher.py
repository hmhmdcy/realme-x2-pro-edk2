#!/usr/bin/python3
"""449-compatible probe launcher with the target account's personal environment."""
from pathlib import Path
import os,pwd,stat,sys

UID=10000
RUNTIME_PARENT=Path('/run/user/10000')
XDG_HOME_DEFAULTS={'XDG_CONFIG_HOME':'.config','XDG_DATA_HOME':'.local/share',
                   'XDG_CACHE_HOME':'.cache','XDG_STATE_HOME':'.local/state'}


def personal_directory(value,home,uid):
    """Accept a usable absolute target-user path, without creating directories."""
    if not value or '\0' in value or not Path(value).is_absolute():return False
    try:
        candidate=Path(value).resolve(strict=False)
        personal=Path(home).resolve(strict=False)
        inside=candidate==personal or personal in candidate.parents
        try:
            info=candidate.stat()
            if not stat.S_ISDIR(info.st_mode):return False
            if not inside and info.st_uid!=uid:return False
        except FileNotFoundError:
            if not inside:return False
        ancestor=candidate
        while True:
            try:
                info=ancestor.stat();break
            except FileNotFoundError:
                if ancestor.parent==ancestor:return False
                ancestor=ancestor.parent
        return stat.S_ISDIR(info.st_mode) and os.access(ancestor,os.X_OK)
    except (OSError,RuntimeError):return False


def runtime_directory(value,uid):
    if not value or '\0' in value or not Path(value).is_absolute():return False
    try:
        path=Path(value);info=path.stat()
        return (not path.is_symlink() and stat.S_ISDIR(info.st_mode) and info.st_uid==uid
                and stat.S_IMODE(info.st_mode)==0o700 and os.access(path,os.R_OK|os.W_OK|os.X_OK))
    except OSError:return False


def target_environment(account,inherited):
    # Called after setuid, so access checks use the real target identity/ACLs.
    assert account.pw_uid==UID and Path(account.pw_dir).is_absolute() and '\0' not in account.pw_dir
    environment=dict(inherited)
    environment.update(HOME=account.pw_dir,USER=account.pw_name,LOGNAME=account.pw_name)
    for key,suffix in XDG_HOME_DEFAULTS.items():
        if not personal_directory(environment.get(key),account.pw_dir,UID):
            environment[key]=str(Path(account.pw_dir)/suffix)
    if not runtime_directory(environment.get('XDG_RUNTIME_DIR'),UID):
        assert runtime_directory(str(RUNTIME_PARENT),UID),'Target runtime directory is not private/usable'
        environment['XDG_RUNTIME_DIR']=str(RUNTIME_PARENT)
    return environment


def checked_program(directory,name):
    supplied=Path(directory)
    assert supplied.is_absolute() and not supplied.is_symlink()
    root=supplied.resolve(strict=True);parent=RUNTIME_PARENT.resolve(strict=True)
    assert root.parent==parent and root.name.startswith('k449-user-')
    info=root.stat();assert stat.S_ISDIR(info.st_mode) and info.st_uid==UID and stat.S_IMODE(info.st_mode)==0o700
    assert name and Path(name).name==name and name not in ['.','..'] and '\0' not in name
    program=root/name;assert not program.is_symlink()
    info=program.stat()
    assert stat.S_ISREG(info.st_mode) and info.st_uid==UID and info.st_mode&stat.S_IXUSR
    assert not info.st_mode&(stat.S_ISUID|stat.S_ISGID)
    return root,program


def main():
    assert os.geteuid()==0 and len(sys.argv)>=3
    account=pwd.getpwuid(UID)
    root,program=checked_program(sys.argv[1],sys.argv[2])
    inherited=dict(os.environ)
    os.umask(0o077);os.initgroups(account.pw_name,account.pw_gid);os.setgid(account.pw_gid);os.setuid(UID)
    assert os.getuid()==os.geteuid()==UID and os.getgid()==account.pw_gid
    assert int(next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('CapEff:')),16)==0
    environment=target_environment(account,inherited)
    os.chdir(root);os.execve(str(program),[str(program),*sys.argv[3:]],environment)


if __name__=='__main__':main()
