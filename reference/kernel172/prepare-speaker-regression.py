from pathlib import Path
import ast

ref = Path(__file__).parent
for name in ['capture-acoustic.py','analyze-acoustic.py','test-desktop-acoustic.py','analyze-desktop.py']:
    s = (ref.parent / 'kernel171' / name).read_text()
    s = s.replace('k171-', 'k172-').replace('kernel171','kernel172').replace('stage=171','stage=172')
    s = s.replace("startswith('#168 ')","startswith('#172 ')").replace('kernel_build=168','kernel_build=172')
    if name == 'capture-acoustic.py':
        token = "assert os.uname().version.startswith('#172 ')"
        assert token in s
        s = s.replace(token, '''for jack_name in ['Headphone Jack', 'Mic Jack']:
    jack_text = subprocess.check_output(['amixer','-c','0','cget',"iface=CARD,name='" + jack_name + "'"], text=True)
    assert re.search(r': values=(.*)',jack_text)[1].strip() == 'off', jack_name
''' + token)
    ast.parse(s)
    assert not (ref / name).exists()
    (ref / name).write_text(s)
print('K172_REGRESSION_TOOLS_PREPARED',flush=True)
