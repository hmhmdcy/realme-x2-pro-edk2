"""Targeted offline regressions: real host/speaker methods, mocked PA and pipes only."""
from pathlib import Path,PureWindowsPath
from types import SimpleNamespace
from unittest.mock import patch
import argparse,contextlib,copy,hashlib,importlib.util,io,json,os,re,shlex,tempfile,time

ROOT=Path(__file__).resolve().parents[3]
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result
def rejected(function,*args):
    try:function(*args)
    except (RuntimeError,ValueError):return True
    raise AssertionError('Expected the actual method to reject this input')

def playback_case(speaker,output,mode):
    state=dict(started=False,samples=0,volume_requests=[],mute_requests=[],player=None,contexts=[])
    sink=dict(name='fixture_sink',index=7,mute=False,volume={'mono':{'value':6554}})
    stream=dict(index=8,sink=7,mute=False,corked=False,properties={
        'application.name':'samurai-bt-low-volume-test','application.process.id':'4242'})
    obj=object.__new__(speaker.Window)
    obj.args=SimpleNamespace(output=output,peer_path='/fixture/peer')
    obj.deadline=time.monotonic()+30;obj.stop=False;obj.capture=None;obj.player=None
    obj.current_sink=None;obj.rounds=[];obj.errors=[];obj.note=lambda *a,**k:None
    def current_sink(*args,**kwargs):
        if state['started']:
            state['samples']+=1
            if mode=='midplay_mute' and state['samples']>=2:sink['mute']=True
        return copy.deepcopy(sink)
    obj.sink=current_sink
    def audio(*args,**kwargs):
        if args[:1]==('set-sink-mute',):
            assert args[1]=='fixture_sink'
            state['mute_requests'].append(args[2]);sink['mute']=args[2]=='1';return ''
        if args[:1]==('set-sink-volume',):
            assert args[1:] == ('fixture_sink','10%')
            state['volume_requests'].append(args[2]);return ''
        assert args==('-f','json','list','sink-inputs') and kwargs.get('json_output')
        return [] if mode=='missing_stream' else [copy.deepcopy(stream)]
    obj.audio=audio
    obj.objects=lambda:{'/fixture/transport':{'org.bluez.MediaTransport1':{'Device':'/fixture/peer','State':'active'}}}
    class PipePlayer:
        def __init__(self,argv,**kwargs):
            assert argv[0]=='paplay' and '--device=fixture_sink' in argv and '--volume=65536' in argv
            state['contexts'].append({k:kwargs[k] for k in ['env','user','group','extra_groups']})
            self.pid=4242;self.returncode=None;self.received=bytearray();self.terminated=False
            self.reader,writer=os.pipe();os.set_blocking(self.reader,False)
            self.stdin=os.fdopen(writer,'wb',buffering=0)
            state['started']=True;state['player']=self
        def poll(self):
            if self.returncode is not None:return self.returncode
            while True:
                try:data=os.read(self.reader,65536)
                except BlockingIOError:break
                if not data:break
                self.received.extend(data)
            if self.stdin.closed:
                self.returncode=0;os.close(self.reader)
            return self.returncode
        def terminate(self):
            self.terminated=True
            if not self.stdin.closed:self.stdin.close()
            if self.returncode is None:os.close(self.reader)
            self.returncode=-15
        kill=terminate
        def wait(self,*args,**kwargs):return self.returncode
    account=SimpleNamespace(pw_dir=str(output),pw_gid=10001,pw_name='fixture-user')
    def pactl(argv,**kwargs):
        assert argv==['pactl','get-default-sink']
        state['contexts'].append({k:kwargs[k] for k in ['env','user','group','extra_groups']})
        return SimpleNamespace(returncode=0,stderr='',stdout='fixture_sink\n')
    with patch.object(speaker.pwd,'getpwuid',return_value=account) as lookup, \
            patch.object(speaker.subprocess,'Popen',PipePlayer),patch.object(speaker.subprocess,'run',pactl):
        assert speaker.Window.audio(obj,'get-default-sink')=='fixture_sink'
        if mode=='normal':obj.play_quiet(1)
        else:rejected(obj.play_quiet,1)
    assert all(call.args==(10000,) for call in lookup.call_args_list)
    assert len(state['contexts'])==2 and state['contexts'][0]==state['contexts'][1]
    credentials=state['contexts'][0];environment=credentials['env']
    assert credentials['user']==10000 and credentials['group']==10001 and credentials['extra_groups']==[]
    assert environment['HOME']==str(output) and environment['USER']==environment['LOGNAME']=='fixture-user'
    assert environment['PULSE_SERVER']=='unix:/run/user/10000/pulse/native' and environment['XDG_RUNTIME_DIR']=='/run/user/10000'
    assert state['mute_requests'][-1]=='1' and state['volume_requests']==['10%'] and len(obj.rounds)==1
    record=obj.rounds[0]
    if mode=='normal':
        assert record['pcm_bytes_sent']==192000==len(state['player'].received)
        assert record['local_mute_checks_passed'] and record['own_stream_active_on_exact_sink_observed']
        assert all(row['sink_mute'] is False for row in record['playback_observations'])
    else:
        assert 'error_private' in record
        if mode=='midplay_mute':assert state['player'].terminated and 'muted' in record['error_private']
    return True

def duration_case(host,root):
    args=SimpleNamespace(output=root/'host-window',remote_output='/var/lib/samurai/bt-le-duration-fixture',
        charging_manifest_sha256='0'*64,central_exe=Path('/not-executed/central.exe'))
    calls=[]
    def ssh(command,**kwargs):
        calls.append((shlex.split(command),kwargs))
        ready=bool(kwargs.get('input',b'').startswith(b'from pathlib import Path'))
        stdout=json.dumps(dict(registered=True,stopping=False,finished=False,remaining_seconds=66)).encode() if ready else b''
        return SimpleNamespace(returncode=0,stdout=stdout,stderr=b'')
    def process(argv,**kwargs):
        assert argv[:2]==['wslpath','-w']
        return SimpleNamespace(stdout='E:/not-executed/'+Path(argv[2]).name+'\n')
    def coordinate(server_call,ready_call,client_call):
        assert server_call()==0 and ready_call()['remaining_seconds']==66
        return dict(windows_client_started=False,server_exit=0,server_terminal=True)
    assert host.SECONDS==60 and host.MINIMUM_REMAINING==45
    with patch.object(host,'SECONDS',67),patch.object(host,'coordinate',coordinate), \
            patch.object(host.subprocess,'run',process),patch.dict('sys.modules',{'host':SimpleNamespace(ssh=ssh)}), \
            contextlib.redirect_stdout(io.StringIO()):
        assert host.eligible(dict(registered=True,remaining_seconds=66),20)
        assert host.run(args,b'fixture-server-not-executed','/not-read/guard','02:11:22:33:44:55',
            dict(total_timeout_seconds=30))==1
    native=[call for call in calls if '-u' in call[0]][0]
    assert native[0][native[0].index('--seconds')+1]=='67'
    assert native[0][:7]==['timeout','-s','TERM','-k','5','105','python3'] and native[1]['timeout']==125
    query=[call for call in calls if call[1].get('input',b'').startswith(b'from pathlib import Path')][0]
    assert b'round(67-(' in query[1]['input'] and b'WINDOW_SECONDS' not in query[1]['input']
    assert query[0][:6]==['timeout','-s','TERM','-k','2','16'] and query[1]['timeout']==25
    assert host.MINIMUM_REMAINING==45 and json.loads((args.output/'windows-config-private.json').read_text())['total_timeout_seconds']==30
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert args.output.is_absolute() and not args.output.exists()
    host_path=ROOT/'reference/bluetooth-20261023/run-gatt-window.py'
    speaker_path=ROOT/'reference/bluetooth-speaker-20261023/low-volume-speaker.py'
    host=module(host_path,'fixed_host_window');speaker=module(speaker_path,'fixed_quiet_speaker')
    central=(ROOT/'reference/bluetooth-windows-central-20261023/windows-gatt-central.cs').read_text()
    windows_root=PureWindowsPath(re.search(r'PrivateRoot = @"([^"]+)"',central).group(1))
    assert str(windows_root).replace('\\','/').lower()=='e:/edk2-samurai-out/bluetooth-windows-central-20261023'
    good=host.CENTRAL_PRIVATE_ROOT/'future-run';bad=host.PRIVATE_ROOT/'bluetooth-20261023/gatt-r3'
    host.require_central_output(good);rejected(host.require_central_output,bad)
    rejected(host.preflight,SimpleNamespace(output=bad))  # No baseline/SSH/client access is reached.
    assert PureWindowsPath('E:/edk2-samurai-out/bluetooth-windows-central-20261023/future-run/windows-config-private.json').is_relative_to(windows_root)
    cases=dict(path_contract_matches_unchanged_central=True,wrong_output_rejected_before_baseline_or_transport=True)
    # Exercise the actual state validator directly for mute/routing failures.
    obj=object.__new__(speaker.Window)
    sink=dict(name='fixture_sink',index=7,mute=False,volume={'mono':{'value':6554}})
    stream=dict(index=8,sink=7,mute=False,corked=False,properties={
        'application.name':'samurai-bt-low-volume-test','application.process.id':'4242'})
    obj.sink=lambda:copy.deepcopy(sink);obj.audio=lambda *a,**k:[copy.deepcopy(stream)]
    assert obj.playback_state('fixture_sink',7,4242)['own_stream_active']
    for label,mutation,undo in [
        ('sink_mute_rejected',lambda:sink.update(mute=True),lambda:sink.update(mute=False)),
        ('unknown_mute_rejected',lambda:sink.update(mute=None),lambda:sink.update(mute=False)),
        ('stream_mute_rejected',lambda:stream.update(mute=True),lambda:stream.update(mute=False)),
        ('moved_stream_rejected',lambda:stream.update(sink=9),lambda:stream.update(sink=7))]:
        mutation();rejected(obj.playback_state,'fixture_sink',7,4242);undo();cases[label]=True
    with tempfile.TemporaryDirectory(prefix='samurai-host-static-') as temporary:
        for mode in ['normal','midplay_mute','missing_stream']:
            output=Path(temporary)/mode;output.mkdir()
            cases['actual_play_quiet_'+mode]=playback_case(speaker,output,mode)
        cases['shared_pulse_context_for_actual_pactl_and_paplay']=True
        cases['seconds_reaches_actual_host_run_ready_and_eligible']=duration_case(host,Path(temporary))
    result=dict(all_passed=all(cases.values()),cases=cases,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [host_path,speaker_path]},
        actual_methods_exercised=True,pa_and_player_modeled=True,pipe_pcm_not_audio_device=True,
        ssh_bluez_winrt_radio_or_audio_device_accessed=False,volume_requested_percent=10)
    with args.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result))
if __name__=='__main__':main()
