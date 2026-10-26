"""Generate bounded common-backend acceptance probes, preserving earlier evidence."""
from pathlib import Path
R=Path(__file__).parent
probe=(R/'immutability-probe.py').read_text()
probe=probe.replace("held=[]", "data['source_plugin']=source.get_factory().get_plugin().get_filename()\ndata['application_copy_env']=os.environ.get('SAMURAI_CAMERA_COPY')\nheld=[]")
probe=probe.replace("assert source.get_factory().get_plugin().get_filename()=='/var/lib/samurai/k263-candidate/libgstpipewire.so'", "assert source.get_factory().get_plugin().get_filename()==('/usr/lib/gstreamer-1.0/libgstpipewire.so' if os.environ.get('K263_SYSTEM_PLUGIN')=='1' else '/var/lib/samurai/k263-candidate/libgstpipewire.so')")
probe=probe.replace("held=[]", "props=devices[0].get_properties();data['remote_node_reliable']=str(props.get_value('node.reliable')) if props.has_field('node.reliable') else None\nheld=[]\nhold_seconds=float(os.environ.get('K263_HOLD_SECONDS','.12'))\nduration=float(os.environ.get('K263_DURATION','12'))")
probe=probe.replace("if int(sys.argv[1]) in [1000000,3000000,3000001,4000000,6000000,6000007]:held.append", "if hold_seconds>0:held.append")
probe=probe.replace("(30 if int(sys.argv[1])==4000000 else 12)","duration")
probe=probe.replace("time.monotonic()-held[0][0]>.12", "time.monotonic()-held[0][0]>hold_seconds")
probe=probe.replace("data['retain_frames_for_ms']=120 if int(sys.argv[1]) in [1000000,3000000,3000001,4000000,6000000,6000007] else 0", "data['retain_frames_for_ms']=hold_seconds*1000")
(R/'advanced-probe.py').write_text(probe)
native=(R/'native-isolated.py').read_text().replace('[6000002,6000003,6000004,6000005,6000006,6000008]','[6000010,6000011,6000012,6000014,6000015,6000016,6000017,6000018,6000019,6000020,6000022,6000023,6000024,6000025,6000026,6000027,6000028,6000029,6000030,6000031,6000032,6000033] + list(range(6000034,6000040))')
native=native.replace('isolated-runner.py','advanced-runner.py').replace('time.monotonic()+40','time.monotonic()+95')
(R/'native-advanced.py').write_text(native)
