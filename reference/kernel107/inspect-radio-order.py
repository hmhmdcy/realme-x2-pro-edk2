from pathlib import Path
import sys
ns={};exec((Path(__file__).parent/'analyse-trace.py').read_text().split("if __name__=='__main__':",1)[0],ns)
for name in sys.argv[1:]:
    f=ns['read_archive'](name)
    print('ARCHIVE',name)
    for l in f['trace.txt'].decode().splitlines():
        if any(e in l for e in ['qrtr_ns_service_announce_new:','samurai_pdm_response:','samurai_core_transaction:']) or ('qrtr_endpoint_tx:' in l and (' type=2 ' in l or ' type=4 ' in l)) or ('qrtr_ns_message: hello ' in l):
            print(l.strip())
