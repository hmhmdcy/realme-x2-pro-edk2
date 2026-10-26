#!/usr/bin/python3
from pathlib import Path
import os,pwd,sys
assert os.geteuid()==0
root=Path(sys.argv[1]).resolve();uid=10000;user=pwd.getpwuid(uid)
assert root.parent==Path('/run/user/10000').resolve() and root.name.startswith('k450-user-') and root.stat().st_uid==uid
program=root/sys.argv[2];assert program.is_file() and program.parent==root
os.umask(0o077);os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(uid)
assert os.getuid()==os.geteuid()==uid
assert int(next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('CapEff:')),16)==0
os.chdir(root);os.execv(str(program),[str(program),*sys.argv[3:]])
