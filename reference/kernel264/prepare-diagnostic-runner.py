"""Extend the saved runner with a native survivor; earlier contexts remain intact."""
from pathlib import Path
R=Path(__file__).parent
p=R/'advanced-runner.py';s=p.read_text();assert 'native-crash' not in s
s=s.replace('range(6000041,6000053)','range(6000041,6000054)')
s=s.replace('6000052:6000015}',"6000052:6000015,6000053:'native-crash'}")
needle=''' elif scenario==6000019:
  gst=start_client('gstreamer-peer',.18,12);native=start_native()'''
assert s.count(needle)==1
s=s.replace(needle,''' elif scenario=='native-crash':
  victim=start_client('crash-client',.35,25);native=start_native()
  time.sleep(7);victim[0].kill();victim[0].wait(timeout=3)
  finish_client(native)
 elif scenario==6000019:
  gst=start_client('gstreamer-peer',.18,12);native=start_native()''')
s=s.replace('assert len(results)==(2 if scenario',"assert len(results)==(1 if scenario=='native-crash' else 2 if scenario")
p.write_text(s)
p=R/'native-advanced.py';s=p.read_text().replace('range(6000041,6000053)','range(6000041,6000054)');p.write_text(s)
p=R/'run.py';s=p.read_text().replace('range(6000041,6000053)','range(6000041,6000054)')
needle="for name in ['advanced-runner.py'";idx=s.index(needle)
s=s[:idx]+'''if mode==6000053:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-tools/native-stream-probe');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o755)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/'native-diagnostic-probe').read_bytes())
'''+s[idx:];p.write_text(s)
