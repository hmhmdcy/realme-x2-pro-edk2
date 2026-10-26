"""Recover the stock parser's embedded manager templates for local analysis."""
from pathlib import Path
import hashlib,json,re,struct
import host

P=host.PRIVATE;parser=Path('/home/cy122/x2pro-linux/parser-k117/ParameterParser')
raw=parser.read_bytes()
if True:
 assert raw[:6]==b'\x7fELF\x02\x01'
 phoff=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
 segments=[struct.unpack_from('<II6Q',raw,phoff+i*stride) for i in range(count)]
 symbols=(P/'parser-symbols-private.txt').read_text()
 def at(va):
  segment=next(s for s in segments if s[0]==1 and s[3]<=va<s[3]+s[5])
  return segment[2]+va-segment[3]
 rows=[]
 for label in ['m_'+stem+'_'+suffix for stem in ['parameterTypes','parameterUtils','parameterModule','parameterSetManager','parameterFileSymbolTable','parameterFileSymbolTableEntry'] for suffix in ['h','cpp']]+['m_defaultSetManagerPartial']:
  sym=re.search(r'^([0-9a-f]+) D (ParameterExporter::'+label+r')$',symbols,re.M);assert sym,label
  pointer=struct.unpack_from('<Q',raw,at(int(sym[1],16)))[0];offset=at(pointer);end=raw.index(b'\0',offset);data=raw[offset:end]
  assert data and b'\n' in data,label
  name=label.removeprefix('m_').replace('_','.').lower() if label!='m_defaultSetManagerPartial' else 'defaultsetmanager.partial'
  (P/'sources'/name).write_bytes(data)
  rows.append(dict(symbol=sym[2],bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),file=name,placeholders=sorted({value.decode() for value in re.findall(rb'\$[A-Z]+\$',data)})))
(P/'manager-template-private.json').write_text(json.dumps(dict(parser_sha256=hashlib.sha256(raw).hexdigest(),templates=rows),indent=2)+'\n')
print(json.dumps(rows,indent=2))
