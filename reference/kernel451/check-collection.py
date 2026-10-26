"""Verify the actual collector preserves empty captures and rejects unsafe members."""
from pathlib import Path
import ast,io,json,tarfile,tempfile
HERE=Path(__file__).resolve().parent
tree=ast.parse((HERE/'collect-prepared.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='unpack')
namespace=dict(Path=Path,tarfile=tarfile,io=io)
exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-collection-unpack','exec'),namespace)
def bundle(rows):
 stream=io.BytesIO()
 with tarfile.open(fileobj=stream,mode='w:gz') as archive:
  for name,kind in rows:
   member=tarfile.TarInfo(name);member.type=kind
   if kind==tarfile.REGTYPE:
    member.size=2;archive.addfile(member,io.BytesIO(b'{}'))
   else:
    member.linkname='other';archive.addfile(member)
 return stream.getvalue()
with tempfile.TemporaryDirectory(prefix='k451-collect-') as directory:
 target=Path(directory)/'valid'
 assert namespace['unpack'](bundle([('state.json',tarfile.REGTYPE),('disabled-120/captures',tarfile.DIRTYPE),('trace-window/captures/test.csv',tarfile.REGTYPE)]),target)==3
 assert (target/'disabled-120/captures').is_dir() and not list((target/'disabled-120/captures').iterdir())
 bad=[[('../bad.log',tarfile.REGTYPE)],[('/bad.log',tarfile.REGTYPE)],[('bad.log',tarfile.SYMTYPE)],[('bad.log',tarfile.LNKTYPE)],[('unexpected',tarfile.DIRTYPE)],[('image.bin',tarfile.REGTYPE)],[('same.json',tarfile.REGTYPE),('same.json',tarfile.REGTYPE)]]
 for index,rows in enumerate(bad):
  output=Path(directory)/str(index)
  try:namespace['unpack'](bundle(rows),output)
  except AssertionError:assert not output.exists()
  else:raise AssertionError('Unsafe collection accepted')
report=dict(stage=451,actual_collection_function_executed=True,empty_captures_directory_preserved=True,nested_csv_preserved=True,unsafe_archives_rejected_before_writes=7,no_phone_sdk_or_build=True,passed=True)
(HERE/'collection-code-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
