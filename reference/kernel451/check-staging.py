"""Run the actual archive validator against valid and malicious local bundles."""
from pathlib import Path
import ast,hashlib,io,json,tarfile,tempfile
HERE=Path(__file__).resolve().parent
tree=ast.parse((HERE/'stage-prepared.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_archive')
environment=dict(Path=Path,hashlib=hashlib,io=io,tarfile=tarfile)
exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-stage-archive-validator','exec'),environment)
def payload(rows):
 data=io.BytesIO()
 with tarfile.open(fileobj=data,mode='w:gz') as archive:
  for name,kind,value in rows:
   member=tarfile.TarInfo(name);member.type=kind
   if kind==tarfile.REGTYPE:
    member.size=len(value);archive.addfile(member,io.BytesIO(value))
   else:
    member.linkname=value;archive.addfile(member)
 return data.getvalue()
with tempfile.TemporaryDirectory(prefix='k451-stage-') as directory:
 source=Path(directory)/'safe';source.write_bytes(b'original')
 files={'safe':str(source)}
 environment['validate_archive'](payload([('safe',tarfile.REGTYPE,b'original')]),files)
 bad=[([('safe',tarfile.REGTYPE,b'changed')],files),
      ([('safe',tarfile.REGTYPE,b'original'),('safe',tarfile.REGTYPE,b'original')],files),
      ([('../safe',tarfile.REGTYPE,b'original')],{'../safe':str(source)}),
      ([('/safe',tarfile.REGTYPE,b'original')],{'/safe':str(source)}),
      ([('safe',tarfile.SYMTYPE,'elsewhere')],files),
      ([('safe',tarfile.LNKTYPE,'elsewhere')],files),
      ([('safe',tarfile.DIRTYPE,'')],files),
      ([('other',tarfile.REGTYPE,b'original')],files)]
 for rows,mapping in bad:
  try:environment['validate_archive'](payload(rows),mapping)
  except AssertionError:pass
  else:raise AssertionError('Unsafe or nonmatching archive accepted')
report=dict(stage=451,actual_archive_validator_executed=True,valid=1,rejected=8,remote_source_syntax_checked_at_execution=True,phone_accessed=False,staged=False,launched=False,passed=True)
(HERE/'staging-code-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
