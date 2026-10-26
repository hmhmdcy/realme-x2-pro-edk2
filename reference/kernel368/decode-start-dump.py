"""Decode a private bounded A5 devcoredump; no automatic device access."""
from pathlib import Path
import json,struct,sys
FORMAT=struct.Struct('<8s12I512s')
def decode(raw):
 if len(raw)!=FORMAT.size:raise ValueError('Expected exactly 568 bytes for A5 dump version 1')
 magic,*fields=FORMAT.unpack(raw)
 if magic!=b'CAMSSA5\0' or fields[0]!=1:raise ValueError('Unsupported A5 diagnostic magic/version')
 version,response,firmware,*rest=fields
 queues=rest[:6];interrupts,watchdogs,protocol_errors,sfr=rest[6:]
 return dict(format='camss-a5-start',version=version,init_response=response,firmware_version=firmware,
     queue_indices=[dict(read=queues[i],write=queues[i+1]) for i in range(0,6,2)],
     interrupts=interrupts,watchdogs=watchdogs,protocol_errors=protocol_errors,
     sfr=sfr.split(b'\0',1)[0].decode('utf-8',errors='replace'))
if __name__=='__main__':
 import host
 assert len(sys.argv)==2,'Pass the path of a previously collected private devcoredump'
 path=Path(sys.argv[1]).resolve();assert path.is_relative_to(host.PRIVATE.parent.resolve()),'Keep raw firmware diagnostics in the private output tree'
 result=decode(path.read_bytes());out=path.with_name(path.stem+'-decoded-private.json');out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(version=result['version'],init_response=result['init_response'],sfr_characters=len(result['sfr']),private_output=str(out))))
