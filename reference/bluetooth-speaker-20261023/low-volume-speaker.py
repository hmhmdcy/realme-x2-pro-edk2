#!/usr/bin/env python3
"""Bounded reconnect test for the existing paired Edifier speaker; no Pair or Agent."""
import argparse
import array
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import pwd
import select
import signal
import subprocess
import sys
import time

LIBRARY_SHA = 'a1f7c44c8e863bf1fcec9e9e507c4e9d621b0410b17e38b9750f76cae33c9004'
SINK_UUID = '0000110b-0000-1000-8000-00805f9b34fb'
TARGET_PERCENT = 10
MAXIMUM_VALUE = int(65536 * .15)  # Includes hardware-volume rounding; never request this ceiling.
PULSE_UID = 10000


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pulse_client_context():
    account=pwd.getpwuid(PULSE_UID)
    runtime='/run/user/'+str(PULSE_UID)
    env=dict(os.environ,HOME=account.pw_dir,USER=account.pw_name,LOGNAME=account.pw_name,
             XDG_RUNTIME_DIR=runtime,PULSE_SERVER='unix:'+runtime+'/pulse/native')
    return dict(env=env,user=PULSE_UID,group=account.pw_gid,extra_groups=[])


def volume_safe(sink):
    channels = sink.get('volume', {}).values()
    values = [row.get('value') for row in channels]
    return bool(values) and all(type(v) is int and 0 <= v <= MAXIMUM_VALUE for v in values)


def tone():
    rate, count = 48000, 96000
    samples = array.array('h', (round(32767 * .10 * math.sin(2 * math.pi * 440 * i / rate) *
                         min(1, i / 2400, (count-1-i) / 2400)) for i in range(count)))
    if sys.byteorder != 'little':
        samples.byteswap()
    return samples.tobytes()


class Window:
    def __init__(self, args, library):
        self.args, self.lib = args, library
        self.deadline = time.monotonic()+90
        self.stop = False
        self.events, self.errors = [], []
        self.bus = self.capture = self.player = None
        self.owner = self.before = self.identity = self.keys = self.default_sink = None
        self.power_attempted = False
        self.connected_by_us = False
        self.current_sink = None
        self.rounds = []
        args.output.mkdir(mode=0o700)
        self.event_file = (args.output/'events-private.jsonl').open('x')

    def note(self, event, **data):
        row = dict(event=event, elapsed_ms=round((time.monotonic()-(self.deadline-90))*1000), **data)
        self.events.append(row)
        self.event_file.write(json.dumps(row)+'\n');self.event_file.flush()

    def budget(self, maximum=8):
        require(not self.stop and time.monotonic()<self.deadline, 'Window stopped or deadline reached')
        require(self.capture is None or self.capture.healthy(), 'Native HCI capture failed')
        return max(.001,min(maximum,self.deadline-time.monotonic()))

    def owner_same(self):
        try:
            return str(self.bus.call_blocking('org.freedesktop.DBus','/org/freedesktop/DBus',
                'org.freedesktop.DBus','GetNameOwner','s',('org.bluez',),timeout=3))==self.owner
        except Exception:return False

    def proxy(self, path):
        return self.bus.get_object(self.owner,path,introspect=False)

    def objects(self, timeout=None):
        return self.proxy('/').GetManagedObjects(dbus_interface='org.freedesktop.DBus.ObjectManager',
                   timeout=timeout or self.budget(4))

    def properties(self, timeout=3):
        return self.proxy('/org/bluez/hci0').GetAll('org.bluez.Adapter1',
                    dbus_interface='org.freedesktop.DBus.Properties',timeout=timeout)

    def powered(self, value, timeout=3):
        require(self.owner_same(),'BlueZ owner changed; do not write another daemon')
        self.proxy('/org/bluez/hci0').Set('org.bluez.Adapter1','Powered',
            self.lib.dbus.Boolean(value,variant_level=1),dbus_interface='org.freedesktop.DBus.Properties',timeout=timeout)

    def audio(self, *arguments, timeout=3, json_output=False):
        result=subprocess.run(['pactl',*arguments],**pulse_client_context(),
                              capture_output=True,text=True,timeout=timeout)
        require(result.returncode==0,'pactl failed: '+result.stderr)
        return json.loads(result.stdout) if json_output else result.stdout.strip()

    def target(self, objects):
        device=objects.get(self.args.peer_path,{}).get('org.bluez.Device1',{})
        require(str(device.get('Address','')).upper()==self.args.peer_address,'Exact paired address changed')
        require(bool(device.get('Paired')) and bool(device.get('Trusted')),'Need existing paired/trusted target')
        require(any(s in str(device.get('Name','')).casefold() for s in ['edifier','漫步者']),
                'Target is not the explicitly requested Edifier speaker')
        require(SINK_UUID in [str(s).lower() for s in device.get('UUIDs',[])],'No remote A2DP Sink declaration')
        return device

    def sink(self, required=True):
        address=self.args.peer_address.casefold()
        cards=self.audio('-f','json','list','cards',json_output=True)
        cards=[r for r in cards if str(r.get('properties',{}).get('device.string','')).casefold()==address or
                 str(r.get('properties',{}).get('bluez.path',''))==self.args.peer_path]
        if not cards and not required:return None
        require(len(cards)==1,'Need exactly one PulseAudio card for this exact paired peer')
        rows=self.audio('-f','json','list','sinks',json_output=True)
        module_id=str(cards[0].get('owner_module'))
        require(module_id.isdecimal() and 0<=int(module_id)<0xffffffff,'Exact card has no module identity')
        matches=[r for r in rows if str(r.get('owner_module'))==module_id and
                 r.get('properties',{}).get('bluetooth.protocol')=='a2dp_sink']
        if not matches and not required:return None
        require(len(matches)==1,'Need exactly one PulseAudio sink for this exact paired peer')
        require(matches[0].get('properties',{}).get('bluetooth.protocol')=='a2dp_sink',
                'Exact peer sink is not the requested A2DP playback profile')
        return matches[0]

    def wait_for(self, predicate, seconds):
        end=min(self.deadline,time.monotonic()+seconds)
        while time.monotonic()<end:
            self.budget()
            if predicate():return
            time.sleep(.1)
        raise RuntimeError('Bounded state wait expired')

    def playback_state(self, name, sink_index, process_id=None):
        sink=self.sink()
        require(str(sink.get('name'))==name and sink.get('index')==sink_index,
                'Exact speaker sink changed during playback')
        require(volume_safe(sink),'Speaker volume exceeded the low-volume ceiling')
        require(sink.get('mute') is False,'Exact speaker sink is muted or mute state is unknown')
        observation=dict(sink_index=sink_index,sink_mute=False,
            sink_volume_values=[row['value'] for row in sink['volume'].values()],
            own_stream_present=False,own_stream_active=False)
        if process_id is not None:
            inputs=self.audio('-f','json','list','sink-inputs',json_output=True)
            own=[row for row in inputs if
                 str(row.get('properties',{}).get('application.process.id'))==str(process_id) and
                 row.get('properties',{}).get('application.name')=='samurai-bt-low-volume-test']
            require(len(own)<=1,'More than one stream claims this test process identity')
            if own:
                stream=own[0]
                require(stream.get('sink')==sink_index,'Test stream moved away from the exact speaker')
                require(stream.get('mute') is False,'Test stream is muted or mute state is unknown')
                require(type(stream.get('corked')) is bool,'Test stream cork state is unknown')
                observation.update(own_stream_present=True,own_stream_index=stream.get('index'),
                    own_stream_mute=False,own_stream_corked=stream['corked'],own_stream_active=not stream['corked'])
        return observation

    def connect(self):
        require(self.owner_same(),'BlueZ owner changed')
        # Trusted existing peer needs no new agent, pairing or trust mutation.
        self.connected_by_us=True
        self.proxy(self.args.peer_path).ConnectProfile(SINK_UUID,dbus_interface='org.bluez.Device1',timeout=self.budget(12))
        self.wait_for(lambda:bool(self.target(self.objects()).get('Connected')),5)
        self.note('known_paired_acl_connected')
        self.wait_for(lambda:self.sink(required=False) is not None,5)
        self.note('known_paired_profile_connected')

    def disconnect(self, timeout=5):
        device=self.target(self.objects(timeout=timeout))
        if device.get('Connected'):
            self.proxy(self.args.peer_path).Disconnect(dbus_interface='org.bluez.Device1',timeout=timeout)
        self.wait_for(lambda:not bool(self.target(self.objects()).get('Connected')),5)
        self.note('known_peer_disconnected')

    def play_quiet(self, sequence):
        sink=self.sink();name=str(sink['name']);sink_index=sink['index'];self.current_sink=name
        self.audio('set-sink-mute',name,'1')
        self.audio('set-sink-volume',name,str(TARGET_PERCENT)+'%')
        quiet=self.sink()
        require(quiet.get('mute') is True and volume_safe(quiet),'Low-volume mute gate failed')
        # No stream is sent until the exact sink has been muted, lowered and read back.
        self.audio('set-sink-mute',name,'0')
        first_observation=self.playback_state(name,sink_index)
        client_context=pulse_client_context()
        payload=tone();sent=0;transport_active=False;stream_active=False;last_check=0
        error_log=(self.args.output/('paplay-'+str(sequence)+'-stderr-private.log')).open('xb')
        record=dict(sequence=sequence,requested_sink_percent=TARGET_PERCENT,
                    pcm_peak_fraction=.10,seconds=2,automatic_volume_escalation=False,
                    playback_observations=[first_observation])
        try:
            self.player=subprocess.Popen(['paplay','--raw','--format=s16le','--rate=48000','--channels=1',
                 '--volume=65536','--client-name=samurai-bt-low-volume-test','--device='+name],
                 stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=error_log,
                  **client_context)
            os.set_blocking(self.player.stdin.fileno(),False)
            end=min(self.deadline,time.monotonic()+8)
            while self.player.poll() is None and time.monotonic()<end:
                self.budget()
                if time.monotonic()-last_check>=.2:
                    observation=self.playback_state(name,sink_index,self.player.pid)
                    record['playback_observations'].append(observation)
                    stream_active|=observation['own_stream_active']
                    objects=self.objects()
                    transport_active|=any(str(i.get('org.bluez.MediaTransport1',{}).get('Device',''))==self.args.peer_path and
                        str(i['org.bluez.MediaTransport1'].get('State',''))=='active' for i in objects.values())
                    last_check=time.monotonic()
                if sent<len(payload):
                    if select.select([], [self.player.stdin], [], .05)[1]:
                        try:sent+=os.write(self.player.stdin.fileno(),payload[sent:sent+8192])
                        except BlockingIOError:pass
                elif not self.player.stdin.closed:self.player.stdin.close()
                time.sleep(.01)
            require(self.player.poll() is not None,'paplay exceeded its bounded duration')
            record.update(paplay_exit=self.player.returncode,pcm_bytes_sent=sent,
                          media_transport_active_observed=transport_active,volume_checks_passed=True,
                          local_mute_checks_passed=True,own_stream_active_on_exact_sink_observed=stream_active)
            require(self.player.returncode==0 and sent==len(payload) and transport_active and stream_active,
                    'Playback path or exact unmuted stream was not observed')
        except Exception as error:
            record['error_private']=repr(error)
            raise
        finally:
            if self.player and self.player.poll() is None:
                self.player.terminate()
                try:self.player.wait(2)
                except subprocess.TimeoutExpired:self.player.kill();self.player.wait(2)
            self.player=None;error_log.close()
            try:self.audio('set-sink-mute',name,'1')
            except Exception as error:self.errors.append('mute after playback: '+repr(error))
            self.rounds.append(record)
        self.note('low_volume_playback_completed',sequence=sequence)

    def run(self):
        cleanup={}
        try:
            require(os.geteuid()==0,'Native test requires the existing root transport')
            self.identity=self.lib.runtime_identity(self.args)
            self.keys=self.lib.key_fingerprint(Path('/var/lib/bluetooth'))
            self.bus=self.lib.dbus.SystemBus(private=True)
            self.owner=str(self.bus.call_blocking('org.freedesktop.DBus','/org/freedesktop/DBus',
                'org.freedesktop.DBus','GetNameOwner','s',('org.bluez',),timeout=3))
            objects=self.objects();self.target(objects);self.before=self.properties()
            require(not self.before.get('Discovering'),'Another discovery is active')
            require(not any(i.get('org.bluez.Device1',{}).get('Connected') for i in objects.values()),'Existing Bluetooth link active')
            require(not int(objects['/org/bluez/hci0']['org.bluez.LEAdvertisingManager1']['ActiveInstances']),
                    'Another advertisement is active')
            self.default_sink=self.audio('get-default-sink')
            inputs=self.audio('-f','json','list','sink-inputs',json_output=True)
            require(all(i.get('corked') is True or i.get('mute') is True for i in inputs),
                    'Existing active audio stream; do not risk moving or mixing it')
            self.capture=self.lib.NativeMonitorCapture(self.args.output/'hci-monitor-private.jsonl')
            if not self.before.get('Powered'):
                self.power_attempted=True;self.powered(True,self.budget(5))
            self.connect();self.play_quiet(1);self.disconnect()
            self.connect();self.play_quiet(2)
        except Exception as error:
            self.errors.append(repr(error))
            try:
                (self.args.output/'failure-state-private.json').write_text(json.dumps(dict(
                    objects=self.objects(timeout=3),cards=self.audio('-f','json','list','cards',json_output=True),
                    sinks=self.audio('-f','json','list','sinks',json_output=True)),default=str,indent=2)+'\n')
            except Exception as capture_error:self.errors.append('failure snapshot: '+repr(capture_error))
        finally:
            safe=False
            try:safe=self.identity is not None and self.lib.runtime_identity(self.args)==self.identity and self.owner_same()
            except Exception as error:self.errors.append('cleanup guard: '+repr(error))
            if safe:
                if self.current_sink:
                    try:self.audio('set-sink-mute',self.current_sink,'1')
                    except Exception:pass  # Sink may have disappeared after the first disconnect.
                if self.connected_by_us:
                    try:
                        obj=self.objects(timeout=3)
                        if self.target(obj).get('Connected'):
                            self.proxy(self.args.peer_path).Disconnect(dbus_interface='org.bluez.Device1',timeout=3)
                        cleanup['known_peer_disconnected']=not bool(self.target(self.objects(timeout=3)).get('Connected'))
                    except Exception as error:self.errors.append('disconnect: '+repr(error))
                if self.power_attempted:
                    try:self.powered(bool(self.before['Powered']));cleanup['powered_restored']=bool(self.properties()['Powered'])==bool(self.before['Powered'])
                    except Exception as error:self.errors.append('power restore: '+repr(error))
                try:
                    current=self.audio('get-default-sink')
                    if self.default_sink and current!=self.default_sink:self.audio('set-default-sink',self.default_sink)
                    cleanup['default_sink_restored']=self.audio('get-default-sink')==self.default_sink
                except Exception as error:self.errors.append('default sink restore: '+repr(error))
            else:cleanup['runtime_guard_and_owner_still_match']=False
            if self.capture:
                try:
                    self.capture.close();cleanup['native_monitor_closed']=self.capture.closed
                    cleanup['native_monitor_packets']=self.capture.packet_count
                    cleanup['native_monitor_reader_stopped']=not self.capture.thread.is_alive()
                    if self.capture.error:self.errors.append('native monitor: '+self.capture.error)
                except Exception as error:self.errors.append('monitor close: '+repr(error))
            try:
                cleanup['keys_unchanged']=self.keys is not None and self.lib.key_fingerprint(Path('/var/lib/bluetooth'))==self.keys
                cleanup['runtime_identity_unchanged']=self.identity is not None and self.lib.runtime_identity(self.args)==self.identity
                if self.before and safe:
                    after=self.properties()
                    cleanup['adapter_properties_restored']=all(after.get(k)==self.before.get(k) for k in
                        ['Powered','Pairable','Discoverable','PairableTimeout','DiscoverableTimeout','Alias'])
            except Exception as error:self.errors.append('final readback: '+repr(error))
            if self.bus:self.bus.close()
            passed=len(self.rounds)==2 and all(r.get('paplay_exit')==0 for r in self.rounds) and not self.errors and all(v for k,v in cleanup.items() if k!='native_monitor_packets')
            report=dict(passed=passed,rounds=self.rounds,cleanup=cleanup,errors=self.errors,
                new_pair_or_trust_operations=False,actual_listener_confirmed_audible=False,
                hearing_confirmation_separate=True,automatic_volume_escalation=False)
            (self.args.output/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
            self.event_file.close()
            print(json.dumps(dict(terminal=True,software_path_passed=passed,low_volume_rounds=len(self.rounds),listener_confirmation_pending=True)))
        return 0 if passed else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gatt-library-source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--peer-path',required=True)
    parser.add_argument('--peer-address',required=True)
    parser.add_argument('--boot-guard-file',required=True)
    parser.add_argument('--charging-manifest-sha256',required=True)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--window-confirmed',action='store_true')
    args=parser.parse_args()
    require(hashlib.sha256(args.gatt_library_source.read_bytes()).hexdigest()==LIBRARY_SHA,'Unreviewed shared guard/capture source')
    require(args.output.is_absolute() and not args.output.exists() and args.output.parent.is_dir(),'Use new native private output')
    require(args.peer_path.startswith('/org/bluez/hci0/dev_'),'Unexpected adapter or target path')
    import re
    require(re.fullmatch(r'[0-9A-F]{2}(?::[0-9A-F]{2}){5}',args.peer_address),'Invalid exact private address')
    require(args.peer_path.endswith(args.peer_address.replace(':','_')),'Address/path mismatch')
    if not args.run:
        print(json.dumps(dict(offline_arguments_valid=True,radio_or_device_accessed=False)));return 0
    require(args.window_confirmed,'Need the current explicit device handoff')
    spec=importlib.util.spec_from_file_location('speaker_guard_capture',args.gatt_library_source)
    lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
    window=Window(args,lib)
    signal.signal(signal.SIGTERM,lambda *_:setattr(window,'stop',True))
    signal.signal(signal.SIGINT,lambda *_:setattr(window,'stop',True))
    return window.run()


if __name__=='__main__':sys.exit(main())
