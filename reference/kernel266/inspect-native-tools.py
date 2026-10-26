import host,json,shlex
code="import subprocess,json;q=subprocess.run(['cam','--help'],capture_output=True);print(json.dumps([x for x in (q.stdout+q.stderr).decode().splitlines() if any(k in x for k in ['camera','capture','stream','file'])]))"
q=host.ssh('python3 -c '+shlex.quote(code),timeout=12);print(q.stdout.decode())

