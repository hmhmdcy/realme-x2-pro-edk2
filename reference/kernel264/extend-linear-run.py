from pathlib import Path
R=Path(__file__).parent
p=R/'advanced-runner.py';s=p.read_text().replace('range(6000041,6000054)','range(6000041,6000057)')
s=s.replace("6000053:'native-crash'}", "6000053:'native-crash',6000054:'native-crash',6000055:6000018,6000056:'native-crash'}")
p.write_text(s)
p=R/'native-advanced.py';s=p.read_text().replace('range(6000041,6000054)','range(6000041,6000057)');p.write_text(s)
p=R/'run.py';s=p.read_text().replace('range(6000041,6000054)','range(6000041,6000057)')
idx=s.index("for name in ['advanced-runner.py'")
s=s[:idx]+'''if mode in [6000054,6000056]:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-tools/native-stream-probe');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o755)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/'native-linear-probe').read_bytes())
if mode==6000055:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-spa/libcamera/libspa-libcamera.so');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/'libspa-libcamera-reset-output.so').read_bytes())
'''+s[idx:];p.write_text(s)
