def source_check():
    pins=json.loads((HERE/'source-pins.json').read_bytes());values={}
    need(set(pins)=={'binder','binder_delivery','worker','worker_delivery','legacy_delivery','key_transport','profile','profile_delivery','host','remote','supervisor'},'source pin set')
    for name,item in pins.items():
        raw=local(item['path']).read_bytes();need(sha(raw)==item['sha256'] and len(raw)==item['bytes'],'source changed: '+name);values[name]=raw
    need(pins['binder_delivery']['sha256']=='38bd3b781485b53f23a5f1771a7da129b68faec7166d1acecf11d33539113d0f'
         and pins['binder']['sha256']=='d9595cb07d5137c99e348f2422ed6d7784ba00d8e065d9aabe19e005b7c40adb','actual current frozen binder')
    need(pins['worker_delivery']['sha256']=='d43e1e7153a4b9d1c5dd8a27437ff571713f6fbf2cb4d555a6f091e25f9cde97'
         and pins['worker']['sha256']=='6818939b88a51ccd9d0455438c73ac3ad51c26332acdf8d1ea31096bdfc80c47','exact current restore algorithm')
    need(pins['legacy_delivery']['sha256']=='d94d774233aebff0e6fef8cb9d0a8a3e1e3f35d18fda43a70d17981b13012e60'
         and pins['key_transport']['sha256']=='7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c','original once owner/key source')
    need(pins['profile']['sha256']=='bd533c9f8dbe53437805a12186186a55ea7e4d974ae988a229211490f806b904'
         and pins['profile_delivery']['sha256']=='fb8a62a13f96c91c30f4c73e71090684edcebde8ca4f73f53d79132036aa5813','original compressed readonly transfer')
    for delivery,source,filename in [('binder_delivery','binder','bind.py'),('worker_delivery','worker','restore-worker.py'),('profile_delivery','profile','profile.py')]:
        report=json.loads(values[delivery]);need(report['passed'] is True and report['files'][filename]['sha256']==pins[source]['sha256'],'source delivery mismatch')
    binder=load_module(pins['binder']['path'],'current_rollback_connected_frozen_binder');binder.source_check()
    return pins,values
