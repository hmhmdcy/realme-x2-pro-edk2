"""Keep the original cases and add repeated disconnect/recovery on one backend."""
from pathlib import Path
R=Path(__file__).parent
p=R/'advanced-runner.py';s=p.read_text().replace('range(6000041,6000057)','range(6000041,6000067)')
s=s.replace("6000056:'native-crash'}", "6000056:'native-crash',6000057:'repeat-close',6000058:'repeat-crash',6000059:6000014,6000060:6000019,6000061:6000016,6000062:6000015,6000063:'long-hold-close',6000064:6000017,6000065:6000018,6000066:'native-crash'}")
needle=" elif scenario=='native-crash':";assert s.count(needle)==1
s=s.replace(needle,''' elif scenario=='repeat-close':
  for i in range(3):
   short=start_client('short-'+str(i),.12,3);long=start_client('long-'+str(i),.18,9)
   finish_client(short);last=finish_client(long)
   assert last['pts_span_seconds']>7.5,'Remaining client stalled in close round '+str(i)
   time.sleep(.3);fd_counts.append(fd_count())
 elif scenario=='repeat-crash':
  for i in range(3):
   victim=start_client('victim-'+str(i),.35,20);survivor=start_client('survivor-'+str(i),.12,10)
   time.sleep(7);victim[0].kill();victim[0].wait(timeout=3)
   last=finish_client(survivor)
   assert last['pts_span_seconds']>8.5,'Remaining client stalled in crash round '+str(i)
   assert (root/('victim-'+str(i)+'-stderr-private.txt')).read_text().count('got new buffer')>5
   time.sleep(.3);fd_counts.append(fd_count())
 elif scenario=='long-hold-close':
  short=start_client('short-client',.12,6);long=start_client('long-client',1.2,16)
  finish_client(short);last=finish_client(long)
  assert last['pts_span_seconds']>14
 elif scenario=='native-crash':''')
s=s.replace("assert len(results)==(1 if scenario=='native-crash' else", "assert len(results)==(6 if scenario=='repeat-close' else 3 if scenario=='repeat-crash' else 2 if scenario=='long-hold-close' else 1 if scenario=='native-crash' else")
s=s.replace("if scenario in [6000012,6000016]:assert", "if scenario in [6000012,6000016,'repeat-close','repeat-crash']:assert")
p.write_text(s)
p=R/'native-advanced.py';s=p.read_text().replace('range(6000041,6000057)','range(6000041,6000067)');p.write_text(s)
p=R/'run.py';s=p.read_text().replace('range(6000041,6000057)','range(6000041,6000067)');idx=s.index("for name in ['advanced-runner.py'")
s=s[:idx]+'''if mode==6000057:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-core/libpipewire-0.3.so.0');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/'libpipewire-binding-reset.so').read_bytes())
'''+s[idx:];p.write_text(s)
