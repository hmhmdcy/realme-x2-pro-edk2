"""Read-only new-boot preflight, adding the exact bound tele module baseline."""
from pathlib import Path
import ast,importlib.util,re,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('preflight461_for468',HERE.parent/'kernel461/preflight-handoff.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def window_valid(value):
    assert re.fullmatch(r'k473-ipe-capacity-r([1-9]|1[0-9]|20)',value),'Unsupported mode2 window'
base.window_valid=window_valid;base.PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel473/preflight')
original_render=base.render
def render(legacy,owner,adoption,window,expected,owner_sha,nonce):
    source,digest=original_render(legacy,owner,adoption,window,expected,owner_sha,nonce)
    marker='print(json.dumps(dict(schema="samurai-camera-preflight-observation-v1"'
    assert source.count(marker)==1;index=source.index(marker)
    extra='''tele_path=Path(subprocess.check_output(['modinfo','-n','s5k3m5'],text=True).strip())
tele_note=Path('/sys/module/s5k3m5/notes/.note.gnu.build-id')
assert tele_path.is_file() and tele_note.is_file()
assert subprocess.check_output(['modinfo','-F','intree',str(tele_path)],text=True).strip()=='Y'
assert subprocess.check_output(['modinfo','-F','vermagic',str(tele_path)],text=True).split()[0]==os.uname().release
tele_clients=[p for p in Path('/sys/bus/i2c/drivers/s5k3m5').iterdir() if (p/'of_node').exists()]
assert len(tele_clients)==1 and (tele_clients[0]/'power/runtime_status').read_text().strip()=='suspended'
baseline['tele_sensor']=dict(path=str(tele_path),sha256=sha(tele_path),note_sha256=sha(tele_note),
    client=tele_clients[0].name,of_node=str((tele_clients[0]/'of_node').resolve()),runtime_status='suspended')
'''
    source=source[:index]+extra+source[index:];ast.parse(source);return source,digest
base.render=render
if __name__=='__main__':
    assert '--window-id' in sys.argv and '--self-test' not in sys.argv
    base.main()
