from pathlib import Path
import ast
ref=Path(__file__).resolve().parent;p=ref/'samurai-gnss-assist.py';s=p.read_text().replace('import datetime\n','').replace('import hashlib\n','')
start=s.index('    lock = (directory /')
end=s.index('\n\ndef main():',start)
block=s[start:end]
block=block.replace('    try:\n        result = refresh_data', '    result = refresh_data')
# Remove the former narrow finally and unindent its body before adding one whole-operation finally.
begin=block.index('    result = refresh_data')
finish=block.index('    finally:\n        bus.close()\n        lock.close()',begin)
part=block[begin:finish]
part='\n'.join(line[4:] if line.startswith('        ') else line for line in part.splitlines())+'\n'
block=block[:begin]+part
lines=block.splitlines();busline=next(i for i,l in enumerate(lines) if l.strip()=='bus = dbus.SystemBus(private=True)')
prefix='\n'.join(lines[:busline+1])+'\n'
body='\n'.join('    '+line for line in lines[busline+1:])+'\n'
s=s[:start]+prefix+'    try:\n'+body+'    finally:\n        bus.close()\n        lock.close()\n'+s[end:]
ast.parse(s);p.write_text(s)
print('K201_ASSIST_ALL_EARLY_RETURN_AND_ERROR_PATHS_CLOSE_DBUS_AND_LOCK')
