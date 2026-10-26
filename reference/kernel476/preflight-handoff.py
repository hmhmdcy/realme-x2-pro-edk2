"""Render/inspect a fresh476 read-only query; never sends it or opens SSH."""
from pathlib import Path
import argparse,ast,contextlib,hashlib,importlib.util,io,json,re,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

def main():
    extra=argparse.ArgumentParser(add_help=False)
    extra.add_argument('--formal-expected',type=Path,help='Optional already-validated future formal expected wrapper; default is unchanged440/434')
    args,remaining=extra.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    assert '--self-test' not in remaining and '--window-id' in remaining
    spec=importlib.util.spec_from_file_location('guard476',HERE.parent/'kernel284/storage.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.mounted_build()
    spec=importlib.util.spec_from_file_location('preflight473_for476',HERE.parent/'kernel473/preflight-handoff.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);base=old.base
    def window_valid(value):assert re.fullmatch(r'k476-control-delay-r([1-9]|1[0-9]|20)',value)
    base.window_valid=window_valid;base.PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel476/preflight')
    frozen=json.loads(Path('/mnt/e/edk2-samurai-out/kernel476/expected-uname-private.json').read_text())
    loader=base.load_legacy
    def load_legacy():
        legacy=loader()
        if args.formal_expected:
            wrapper=json.loads(args.formal_expected.read_text());assert wrapper['validated'] is True
            expected=wrapper['expected']
            assert set(expected)=={'packages','modules','installed_files','library_sha256','kernel_release'}
            assert expected['kernel_release']==frozen['release']
            assert expected['installed_files']['/usr/lib/libcamera.so.0.7.2']==expected['library_sha256']
            assert set(expected['modules'])=={'qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core'}
            legacy.inputs=lambda:expected
        return legacy
    base.load_legacy=load_legacy
    render=base.render
    def render476(*params):
        source,digest=render(*params)
        needle='guard.read_bytes()==boot'
        assert needle in source
        # Append to the guard assertion line, before subsequent inventory.
        lines=source.splitlines(True)
        i=next(i for i,line in enumerate(lines) if needle in line)
        lines.insert(i+1,'assert os.uname().release=='+repr(frozen['release'])+' and os.uname().version=='+repr(frozen['version'])+'\n')
        source=''.join(lines);ast.parse(source);return source,digest
    base.render=render476
    output=io.StringIO()
    with contextlib.redirect_stdout(output):base.main()
    result=json.loads(output.getvalue())
    if '--request' in remaining:
        request=Path(remaining[remaining.index('--request')+1]);handoff=request.parent/'handoff-private.json'
        data=json.loads(handoff.read_text());data['expected_uname']=frozen
        handoff.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(result,expected_uname_from_frozen363=True,default_formal_baseline_unchanged=args.formal_expected is None)))

if __name__=='__main__':main()
