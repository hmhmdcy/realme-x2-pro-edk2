"""Small offline transaction suite with real atomic file operations."""
from pathlib import Path
import base64
import copy
import importlib.util
import json
import os
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('stage_r7', HERE / 'stage-r7.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
CACHE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
PAYLOAD = (CACHE / 'r7-candidate/source-float-payload.tar.gz').read_bytes()
OLD_USB = (CACHE / 'samurai-usb-input.ko').read_bytes()
OLD_MANIFEST = (CACHE / 'r6-candidate/manifest.json').read_bytes()
assert m.sha(OLD_USB) == m.OLD_USB and m.sha(OLD_MANIFEST) == m.OLD


def request():
    return dict(transaction='source-stage-r7-offline-test', guard=m.GUARD,
                identity=dict(boot_id='11111111-2222-4333-8444-555555555555', serial_sha256='1'*64, compatible_sha256='2'*64),
                window_token='3'*48, old_manifest_sha256=m.OLD, new_manifest_sha256=m.NEW,
                payload_sha256=m.PAYLOAD, payload_base64=base64.b64encode(PAYLOAD).decode())


def observation():
    zero = ['shadow','valid','protection_ok','budget_ua','temp_decic','pack_uv','cell1_uv','cell2_uv','flags','fault',
            'desired_enable','stop_error','latched','thermal_inhibit','cycle_timeout','gauge_current_ua','logical_full',
            'full_holding','hold_requested','full_cause','sw_full_count','recharge_count','gauge_charge_stop']
    s = {k: 0 for k in zero}; s.update(online=1, source_inhibit=1, error=-61, age_ms=-1, session_seconds=100)
    source = dict(online=1,current_max_errno=61,native_ua=100000,usb_type='[Unknown] SDP DCP CDP C')
    return dict(sample=s,source_before=source,source_after=copy.deepcopy(source),
                pmic_before=dict(m.FLOAT),pmic_after=dict(m.FLOAT),registers={'08':8,'13':2},native_retained='Y',
                protection_health='Good',protection_present=1,protection_state=dict(id=0x2719,safety=0,pf=0,error=0,operation=0x386,manufacturing=0x18),
                gauge=dict(temp_decic=241,pack_uv=8400000,flags=0xc0),read_start_boottime=99.2,read_end_boottime=99.8,
                state=dict(taint='0',driver='samurai-mp2650',boot_id=request()['identity']['boot_id'],release=m.RELEASE,
                           camera_pm={'cam':'suspended'},m2m='idle',services=[{'pid':5,'comm':'phosh'}]),
                notes={'samurai-usb-input':'old-usb-note','samurai-mp2650':'charger-note','samurai-gauge-protection':'protection-note'},openrc_started=True)


class FaultOps:
    """Only injected OS boundaries differ; all files/writes/renames are real."""
    def __init__(self, mode=None): self.mode=mode; self.fired=0; self.last_target=None
    def __getattr__(self,name): return getattr(os,name)
    def write(self,fd,data):
        name=os.readlink('/proc/self/fd/'+str(fd))
        if self.mode=='usb-write' and self.fired==0 and '.usb.ko.' in name:
            self.fired=1;raise OSError('injected USB write failure')
        if self.mode in ['manifest-write','rollback-fail'] and self.fired==0 and '.manifest.json.' in name:
            self.fired=1;raise OSError('injected manifest write failure')
        if self.mode=='rollback-fail' and self.fired==1 and '.usb.ko.' in name:
            self.fired=2;raise OSError('injected rollback write failure')
        return os.write(fd,data)
    def replace(self,source,target):
        self.last_target=str(target)
        if self.mode=='unknown' and self.fired==0:
            Path(target).write_bytes(b'foreign unexpected bytes');self.fired=1
            raise OSError('injected unknown rename outcome')
        os.replace(source,target)
        if self.mode=='rename-error-after-commit' and self.fired==0:
            self.fired=1;raise OSError('injected synchronous error after rename')
    def fsync(self,fd):
        if self.mode=='dir-fsync' and self.fired==0 and stat.S_ISDIR(os.fstat(fd).st_mode):
            self.fired=1;raise OSError('injected directory fsync failure')
        os.fsync(fd)


class FilesDevice(m.Device):
    """Real file methods/atomic writer; only device identity/manager edges fake."""
    def __init__(self,root,mode=None):
        super().__init__();self.root=root;self.ops=FaultOps(mode);self.stop_calls=0;self.stop_failure=False
        self.bad_window=False;self.bad_identity=False;self.row=observation();self.verify_calls=[]
        self.paths={m.USB:root/'lib/usb.ko',m.MANIFEST:root/'share/manifest.json'}
        for name,raw in [(m.USB,OLD_USB),(m.MANIFEST,OLD_MANIFEST)]:
            p=self.paths[name];p.parent.mkdir(parents=True);p.write_bytes(raw);p.chmod(0o600)
    def now(self): return 100
    def begin(self,r):
        self.check_window(r);out=self.root/r['transaction'];out.mkdir(mode=0o700)
        self.out=out;self.transaction=r['transaction']
    def check_window(self,r):
        if self.bad_window: raise RuntimeError('lease mismatch')
        if self.bad_identity: raise RuntimeError('identity mismatch')
    def read_owned(self,name): return m.read_owned(self.paths[name])
    def manager(self): self.events.append(['fresh-manager',m.MANAGER]);return {'fresh':True}
    def verify(self,manager):
        self.verify_calls.append(manager);return json.loads(self.read_owned(m.MANIFEST)[0])
    def notes_match(self,manager,meta,use_backup=False):
        if use_backup: assert m.sha((self.out/'usb-before.ko').read_bytes())==m.OLD_USB
        self.events.append(['notes-match',use_backup])
    def observe(self,manager): return copy.deepcopy(self.row)
    def stop(self,manager,old):
        self.stop_calls+=1;self.events.append(['direct-manager-command',m.MANAGER,'stop'])
        if self.stop_failure: raise OSError('stop failed even if later readback inhibited')
    def registers(self,manager): return self.row['registers']
    def replace(self,name,raw,allowed):
        self.events.append(['replace',name,m.sha(raw)])
        return m.atomic_replace(self.paths[name],raw,self.transaction,allowed,self.ops)
    def known_files(self):
        for name in m.FILES:
            raw,mode=self.read_owned(name)
            if mode!=0o600 or m.sha(raw) not in {m.FILES[name],m.OLD_FILES[name]}: raise m.UnknownWriteState('unexpected pair')


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.device=FilesDevice(self.root)
    def stage(self): return m.stage(request(),self.device,execute=True)
    def pair(self): return {n:m.sha(self.device.read_owned(n)[0]) for n in m.FILES}
    def test_inert_import_and_explicit_execute(self):
        fresh=importlib.util.module_from_spec(spec)
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('import read')):spec.loader.exec_module(fresh)
        with self.assertRaises(RuntimeError):m.stage(request(),self.device)
        self.assertEqual(self.device.stop_calls,0)
    def test_exact_payload_and_manifest_delta_only(self):
        files,new=m.unpack(request());self.assertEqual(set(files),{m.USB,m.MANIFEST})
        old=json.loads(OLD_MANIFEST);m.manifest_delta(old,new)
        bad=copy.deepcopy(new);bad['default_charge_cap_ua']=1100000
        with self.assertRaises(RuntimeError):m.manifest_delta(old,bad)
        r=request();r['payload_base64']=base64.b64encode(PAYLOAD+b'x').decode()
        self.assertIsNotNone(m.stage(r,self.device,True)['primary_error']);self.assertEqual(self.device.stop_calls,0)
    def test_success_only_stages_disk_keeps_old_provider_and_inhibit(self):
        result=self.stage();self.assertTrue(result['staged']);self.assertTrue(result['runtime_pending'])
        self.assertEqual(result['phase'],'staged');self.assertEqual(self.pair(),m.FILES)
        self.assertEqual(self.device.stop_calls,1);self.assertEqual(result['resident_usb_sha256'],m.OLD_USB)
        self.assertTrue(result['resident_provider_still_r6']);self.assertFalse(result['source_float_runtime_fixed'])
        self.assertEqual((self.device.out/'usb-before.ko').read_bytes(),OLD_USB)
        self.assertEqual((self.device.out/'manifest-before.json').read_bytes(),OLD_MANIFEST)
        for name in m.FILES:self.assertEqual(self.device.read_owned(name)[1],0o600)
        commands=[x for x in self.device.events if x[0]=='direct-manager-command']
        self.assertEqual(commands,[['direct-manager-command',m.MANAGER,'stop']])
    def test_repeat_refused_preserves_prior_result(self):
        first=self.stage();saved=(self.device.out/'result.json').read_bytes()
        # A fresh device/process with the same transaction has no right to log
        # into the previous result directory after exclusive mkdir is refused.
        self.device.out=None
        again=self.stage();self.assertFalse(again['staged']);self.assertEqual(self.device.stop_calls,1)
        self.assertEqual((self.root/request()['transaction']/'result.json').read_bytes(),saved)
        self.assertTrue(first['staged'])
    def test_each_file_write_failure_restores_exact_old_pair(self):
        for mode in ['usb-write','manifest-write']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                d=FilesDevice(Path(temp),mode);result=m.stage(request(),d,True)
                self.assertFalse(result['staged']);self.assertEqual(result['disk_state'],'r6_pair_restored_inhibited')
                self.assertEqual({n:m.sha(d.read_owned(n)[0]) for n in m.FILES},m.OLD_FILES)
                self.assertEqual(d.stop_calls,1);self.assertEqual(d.registers(None)['08']&0x18,8)
    def test_known_rename_or_directory_sync_failure_rolls_back(self):
        for mode in ['rename-error-after-commit','dir-fsync']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                d=FilesDevice(Path(temp),mode);result=m.stage(request(),d,True)
                self.assertFalse(result['staged']);self.assertFalse(result['unknown_write_state'])
                self.assertEqual(result['disk_state'],'r6_pair_restored_inhibited')
    def test_rollback_failure_does_not_retry_or_auto(self):
        self.device.ops=FaultOps('rollback-fail');result=self.stage()
        self.assertFalse(result['staged']);self.assertIsNotNone(result['recovery_error'])
        self.assertEqual(result['disk_state'],'recovery_failed_inspect_before_boot')
        self.assertEqual(self.pair(),{m.USB:m.NEW_USB,m.MANIFEST:m.OLD})
        self.assertEqual(self.device.stop_calls,1)
    def test_unknown_target_is_preserved_without_blind_rollback(self):
        self.device.ops=FaultOps('unknown');result=self.stage()
        self.assertTrue(result['unknown_write_state']);self.assertFalse(result['staged'])
        self.assertEqual(self.device.paths[m.USB].read_bytes(),b'foreign unexpected bytes')
        self.assertEqual(len([x for x in self.device.events if x[0]=='replace']),1)
        self.assertEqual(self.device.stop_calls,1)
    def test_stop_failure_never_replaces_even_with_later_inhibit(self):
        self.device.stop_failure=True;result=self.stage()
        self.assertFalse(result['staged']);self.assertIsNotNone(result['stop_error'])
        self.assertEqual(self.pair(),m.OLD_FILES);self.assertFalse([x for x in self.device.events if x[0]=='replace'])
    def test_float_or_fresh_protection_failure_prevents_stop_and_disk_writes(self):
        for mutate in ['fault','protection','stale','other-raw']:
            with self.subTest(mutate=mutate),tempfile.TemporaryDirectory() as temp:
                d=FilesDevice(Path(temp))
                if mutate=='fault':d.row['sample']['fault']=1
                elif mutate=='protection':d.row['protection_state']['error']=-5
                elif mutate=='stale':d.row['read_start_boottime']=90
                else:d.row['pmic_after']['0x1308']=0
                result=m.stage(request(),d,True)
                self.assertFalse(result['staged']);self.assertEqual(d.stop_calls,0)
    def test_lease_identity_rejected_before_stop(self):
        for field in ['bad_window','bad_identity']:
            setattr(self.device,field,True);result=self.stage();setattr(self.device,field,False)
            self.assertFalse(result['staged']);self.assertEqual(self.device.stop_calls,0)
            self.assertEqual(self.pair(),m.OLD_FILES)
    def test_actual_device_lease_and_identity_gate(self):
        r=request();serial=b'raw-soc-serial\n';compat=b'realme,samurai\0qcom,sm8150\0'
        r['identity']['serial_sha256']=m.sha(serial);r['identity']['compatible_sha256']=m.sha(compat)
        good=dict(transaction=r['transaction'],owner='charging',token=r['window_token'],boot_id=r['identity']['boot_id'],
                  camera_released=True,bluetooth_released=True,exclusive=True,issued_boottime_s=95,expires_boottime_s=110)
        d=m.Device();d.now=lambda:100
        def text(path,*a,**k):
            if str(path) in ['/proc/sys/kernel/random/boot_id',m.GUARD]:return r['identity']['boot_id']+'\n'
            raise AssertionError(path)
        def raw(path,*a,**k):
            if str(path)=='/sys/devices/soc0/serial_number':return serial
            if str(path)=='/sys/firmware/devicetree/base/compatible':return compat
            raise AssertionError(path)
        with patch.object(m.Path,'read_text',text),patch.object(m.Path,'read_bytes',raw):
            d.read_owned=lambda name:(json.dumps(good).encode(),0o600);d.check_window(r)
            for key,value in [('token','bad'),('bluetooth_released',False),('expires_boottime_s',99),('issued_boottime_s',101),('expires_boottime_s',300)]:
                lease={**good,key:value};d.read_owned=lambda name,v=lease:(json.dumps(v).encode(),0o600)
                with self.assertRaises(RuntimeError):d.check_window(r)
            d.read_owned=lambda name:(json.dumps(good).encode(),0o600)
            bad=copy.deepcopy(r);bad['identity']['serial_sha256']='0'*64
            with self.assertRaises(RuntimeError):d.check_window(bad)


if __name__=='__main__':unittest.main(verbosity=2)
