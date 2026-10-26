from pathlib import Path
import host,importlib.util,json
here=Path(__file__).resolve().parent
selected=host.selected();fn=selected.ssh
spec=importlib.util.spec_from_file_location('direct_recovery',here.parent/'kernel200/host-before-newboot.py');direct=importlib.util.module_from_spec(spec);spec.loader.exec_module(direct)
selected_endpoint=fn.__globals__['_wifi']();direct_endpoint=direct.ssh.__globals__['_wifi']()
failure=(host.PRIVATE/'transport-last-failure-private.log').read_bytes()
print(json.dumps(dict(selected_origin=Path(fn.__globals__['__file__']).parent.name,direct_origin=Path(direct.ssh.__globals__['__file__']).parent.name,same_endpoint=selected_endpoint[1]==direct_endpoint[1],same_ssh_options=selected_endpoint[0].OPTIONS==direct_endpoint[0].OPTIONS,failed_call_used_selected_wifi_address=selected_endpoint[1].encode() in failure,failed_call_used_ipv6_link_local=b'fe80:' in failure,failed_call_timed_out=b'Connection timed out' in failure)))
