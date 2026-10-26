"""Current identity refusal and real same-child terminal tests; no phone PM."""
from pathlib import Path
import ast,copy,hashlib,inspect,json,os,sys,tempfile,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import host
builder=host.load(HERE/'pm-smoke-host.py','current_pm_smoke_builder')
fixture=host.load(host.DEVICE/'test-device.py','current_pm_smoke_fixture')
supervisor=host.load(HERE/'pm-smoke-supervisor.py','current_pm_smoke_supervisor')

class PMChecks(unittest.TestCase):
    def test_actual_generated_launcher_template_parses(self):
        source=ast.parse(inspect.getsource(builder.launch))
        tail=next(n.value for n in ast.walk(source) if isinstance(n,ast.Constant) and isinstance(n.value,bytes) and b'from pathlib import Path' in n.value)
        parsed=ast.parse(b'LAUNCH={}\n'+tail)
        self.assertTrue(parsed.body);self.assertIn(b'.split(bytes([0]))',tail)
        self.assertNotIn(b'\x00',tail)

    def test_wrong_boot_or_sleep_mode_never_reaches_PM(self):
        raw,request=fixture.fixture('forward_504');guard='/var/lib/samurai/irq-native-usb-pm-activate-fixture-adopted/boot-id-private.txt'
        packet=dict(schema='samurai-native-pm-smoke-v1',postboot_request=request,adoption_guard=guard)
        code=builder.worker_code(packet);tree=ast.parse(code)
        # Definitions only: keep actual collector, original PM primitive and body.
        tree.body=[n for n in tree.body if not isinstance(n,ast.If)]
        for wrong_boot in (True,False):
            with tempfile.TemporaryDirectory() as temp:
                directory=Path(temp);guard_file=directory/'guard';guard_file.write_text(request['new_boot_id']+'\n')
                mode=directory/'mode';mode.write_text('[deep]')
                namespace=dict(__name__='pm_definition_test',__file__=str(directory/'worker.py'))
                exec(compile(tree,'<current-pm-worker-test>','exec'),namespace)
                actual=copy.deepcopy(raw['identity_before'])
                if wrong_boot:actual['boot_id']=request['guard']['boot_id']
                namespace['identity']=lambda:actual
                namespace['Path']=lambda value,*args:guard_file if str(value)==guard else mode if str(value)=='/sys/power/mem_sleep' else Path(value,*args)
                called=[];namespace['suspend_once']=lambda *a,**kw:called.append(1)
                with self.assertRaises(AssertionError):namespace['pm_smoke']()
                self.assertEqual(called,[]);self.assertEqual({p.name for p in directory.iterdir()},{'guard','mode'})

    def test_real_worker_terminal_zero_and_failure(self):
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        for code in (0,7):
            with tempfile.TemporaryDirectory() as temp:
                directory=Path(temp);worker=directory/'worker.py';worker.write_text('raise SystemExit('+str(code)+')\n')
                (directory/'launch-private.json').write_text(json.dumps(dict(boot_id=boot,worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest())))
                self.assertEqual(supervisor.supervise(directory),code)
                terminal=json.loads((directory/'worker-terminal-private.json').read_bytes())
                self.assertTrue(terminal['terminal']);self.assertEqual(terminal['returncode'],code)
                self.assertEqual(terminal['pid'],terminal['process']['pid']);self.assertGreater(terminal['process']['startticks'],0)
                with self.assertRaises(FileExistsError):supervisor.supervise(directory)

if __name__=='__main__':unittest.main()
