"""Release the sensor's normal async registration before unloading its module."""
from pathlib import Path
import host,json
here=Path(__file__).resolve().parent;proof=json.loads((here/'imx471-module-build-validation.json').read_text())
assert json.loads((here/'reload-ref-validation.json').read_text())['module_file_matches_original']
text=(here/'install-and-reload.py').read_text();code=text.split("code=r'''",1)[1].split("'''",1)[0]
code=code.replace("out=root/'k215-driver-test'","out=root/'k215-driver-test-r2'")
code=code.replace("unloaded=False;installed=False;failure=None;restored_old=False","unloaded=False;installed=False;unbound=False;failure=None;restored_old=False")
needle="    state['state']='unload-submitted';marker.write_text(json.dumps(state)+'\\n')"
assert code.count(needle)==1
code=code.replace(needle,"""    assert json.loads((root/'k215-driver-test/transition-state-private.json').read_text())['state']=='failed-no-driver-change'
    state['state']='unbind-submitted';marker.write_text(json.dumps(state)+'\\n')
    Path('/sys/bus/i2c/drivers/imx471/unbind').write_text('7-0010')
    unbound=True;assert not Path('/sys/bus/i2c/devices/7-0010/driver').is_symlink()
    (out/'unbound-refcount-private.txt').write_text(Path('/sys/module/imx471/refcnt').read_text())
"""+needle)
start=code.index('except Exception as error:');end=code.index('finally:',start)
code=code[:start]+"""except Exception as error:
    failure=repr(error);(out/'failure-private.txt').write_text(failure)
    if unbound or unloaded:
        if installed and Path('/sys/module/imx471').exists():
            if Path('/sys/bus/i2c/devices/7-0010/driver').is_symlink():Path('/sys/bus/i2c/drivers/imx471/unbind').write_text('7-0010')
            subprocess.run(['modprobe','-r','imx471'],capture_output=True,check=True,timeout=20)
        if installed:
            shutil.copyfile(base/'imx471-original.ko',target);target.chmod(0o644)
            subprocess.run(['depmod','-a'],capture_output=True,check=True,timeout=30)
        if not Path('/sys/module/imx471').exists():subprocess.run(['modprobe','imx471'],capture_output=True,check=True,timeout=20)
        if not Path('/sys/bus/i2c/devices/7-0010/driver').is_symlink():Path('/sys/bus/i2c/drivers/imx471/bind').write_text('7-0010')
        assert Path('/sys/bus/i2c/devices/7-0010/driver').resolve().name=='imx471' and sha(target)==sha(base/'imx471-original.ko')
        restored_old=True
"""+code[end:]
code=code.replace("state['state']='verified' if not failure else 'failed-restored'","state['state']='verified' if not failure else ('failed-restored' if restored_old else 'failed-no-driver-change')")
code=code.replace('new_sensor_module_installed=not failure,','new_sensor_module_installed=not failure,normal_sensor_unbind_used=True,')
code=code.replace('__HASH__',repr(proof['module_sha256'])).replace('__VERMAGIC__',repr(proof['vermagic']))
compile(code,'native-reload-r2','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=150);(host.PRIVATE/'module-reload-r2-host-private.log').write_bytes(p.stdout+p.stderr);report=json.loads(p.stdout);(here/'module-reload-r2-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
