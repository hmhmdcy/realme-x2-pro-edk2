from pathlib import Path
import host,json
code=r'''
import gi,json
gi.require_version('Qmi','1.0');from gi.repository import Qmi,GObject
for cls in [Qmi.Device,Qmi.Client,Qmi.ClientLoc]:GObject.type_class_ref(cls)
names={'Device':['command','command_full','command_full_finish','command_finish','get_next_transaction_id'], 'Client':['get_cid','get_next_transaction_id']}
docs={name:{method:str(getattr(getattr(Qmi,name),method).__doc__) if hasattr(getattr(Qmi,name),method) else None for method in methods} for name,methods in names.items()}
print(json.dumps(dict(signals={name:list(GObject.signal_list_names(getattr(Qmi,name))) for name in ['Device','Client','ClientLoc']},docs=docs)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'raw-api-docs-private.json').write_bytes(p.stdout);print(p.stdout.decode())
