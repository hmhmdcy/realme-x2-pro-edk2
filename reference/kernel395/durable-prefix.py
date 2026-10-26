from pathlib import Path
def source():
 root=Path(__file__).resolve().parent
 code=(root.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':395")
 old="def save(phase,**kw):state.update(phase=phase,**kw);marker.write_text(json.dumps(state,indent=2)+'\\n')"
 new='''def save(phase,**kw):
 state.update(phase=phase,**kw);tmp=root/'state.tmp'
 with tmp.open('w') as stream:
  stream.write(json.dumps(state,indent=2)+'\\n');stream.flush();os.fsync(stream.fileno())
 os.replace(tmp,marker);descriptor=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(descriptor)
 finally:os.close(descriptor)
'''
 assert code.count(old)==1
 return code.replace(old,new)
