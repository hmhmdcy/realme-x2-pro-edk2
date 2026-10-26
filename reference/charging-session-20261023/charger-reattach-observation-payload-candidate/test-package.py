"""Seven affected packaging checks only; no updater process or device access."""
from pathlib import Path
import ast,base64,copy,gzip,importlib.util,io,json,tarfile,tempfile
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('new_two_file_package',HERE/'package.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

def reject(fn):
    try:fn()
    except (ValueError,RuntimeError):return
    raise AssertionError('negative boundary accepted')

def malformed(files,extra=False,mode=0o600):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        for name,raw in sorted({**files,**({'/unexpected':b'x'} if extra else {})}.items()):
            entry=tarfile.TarInfo(name.lstrip('/'));entry.uid=entry.gid=0;entry.uname=entry.gname='root'
            entry.mode=mode;entry.mtime=0;entry.size=len(raw);tar.addfile(entry,io.BytesIO(raw))
    return gzip.compress(stream.getvalue(),mtime=0)

def main():
    details,forward,rollback=p.inputs();cases=[]
    assert details['new_charger']['sha256']==p.NEW and details['old_charger']['sha256']==p.OLD
    assert details['new_charger']['resident_note_sha256']==p.NEW_NOTE and details['old_charger']['resident_note_sha256']==p.OLD_NOTE
    cases.append('actual receipt/ELF/name/vermagic/intree/note and original charger payload bindings')
    baseline=rollback[p.MANIFEST];new=forward[p.MANIFEST]
    assert new.replace(p.NEW.encode(),p.OLD.encode())==baseline and len(new)==len(baseline)
    old=json.loads(baseline);changed=json.loads(new)
    assert all(old[key]==changed[key] for key in old if key not in ('modules','installed_files'))
    for name in ('samurai-usb-input','samurai-gauge-protection'):assert old['modules'][name]==changed['modules'][name]
    reject(lambda:p.new_manifest(baseline.replace(b'900000',b'950000')))
    cases.append('exactly two charger hash spans; other bytes/entries and caps retained; altered base rejected')
    packed=p.archive(forward);assert packed==p.archive(forward);p.check_archive(packed,forward)
    cases.append('forward archive deterministic and exact two-file readback')
    back=p.archive(rollback);p.check_archive(back,rollback)
    original_R8=p.local(details['input_files']['old_R8_archive']['path']).read_bytes()
    reject(lambda:p.check_archive(original_R8,rollback));reject(lambda:p.check_archive(packed,rollback))
    cases.append('rollback contains exact10ec+5fca; original3203 R8 archive or forward cannot substitute')
    reject(lambda:p.check_archive(malformed(forward,extra=True),forward))
    reject(lambda:p.check_archive(malformed(forward,mode=0o644),forward))
    cases.append('extra member and wrong installed metadata rejected')
    with tempfile.TemporaryDirectory(prefix='samurai-two-file-package-test-') as directory:
        root=Path(directory);marker=root/'untouched';marker.write_bytes(b'keep')
        reject(lambda:p.materialize(root,details,forward,rollback));assert marker.read_bytes()==b'keep'
    cases.append('existing output rejected without overwrite')
    updater=HERE.parents[1]/'charging-oem-audit-20261023/r8-update/update-r8.py'
    tree=ast.parse(updater.read_bytes());names={'need','manifest_delta'}
    selected=ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names],type_ignores=[])
    scope={'KO':p.KO,'RELEASE':p.RELEASE,'SERVICE':'/usr/sbin/samurai-charging',
       'SERVICE_SHA':'61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4','HASHES':{p.KO:p.OLD}}
    exec(compile(ast.fix_missing_locations(selected),'<actual old r8 manifest gate>','exec'),scope)
    reject(lambda:scope['manifest_delta'](old,changed))
    cases.append('actual unchanged r8 manifest_delta rejects current IRQ-to-observation pair')
    result={'passed':True,'affected_packaging_checks':len(cases),'checks':[{'case':name,'passed':True} for name in cases],
        'tested_files':{'package.py':p.sha((HERE/'package.py').read_bytes()),'test-package.py':p.sha((HERE/'test-package.py').read_bytes())},
        'actual_old_updater_sha256':p.sha(updater.read_bytes()),'old_updater_function_AST_executed':['need','manifest_delta'],
        'old_matrices_rerun':False,'actual_runtime_identity_request_or_transport_created':False,'device_accessed':False}
    (HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'affected_packaging_checks':len(cases)}))

if __name__=='__main__':main()
