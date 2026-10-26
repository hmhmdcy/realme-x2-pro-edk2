"""Read the standard Gst device provider's target properties, without streaming."""
import json,time,gi
gi.require_version('Gst','1.0')
from gi.repository import Gst,GLib
Gst.init(None);provider=Gst.DeviceProviderFactory.find('pipewiredeviceprovider').get();assert provider.start()
try:
 ctx=GLib.MainContext.default();deadline=time.monotonic()+4
 while time.monotonic()<deadline:
  while ctx.pending():ctx.iteration(False)
  time.sleep(.02)
 devices=[d for d in provider.get_devices() if d.get_display_name()=='Built-in Front Camera'];assert len(devices)==1
 props=devices[0].get_properties()
 result={key:str(props.get_value(key)) for key in ['node.name','node.reliable','node.reliable.broadcast']}
 print(json.dumps(result))
finally:provider.stop()
