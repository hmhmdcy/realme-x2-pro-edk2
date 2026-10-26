import json,socket
s=socket.socket(42,socket.SOCK_DGRAM)
try:
 addr=s.getsockname();s.bind((addr[0],0));bound=s.getsockname()
 print(json.dumps(dict(stage=243,python_qrtr_address_supported=True,bound_port_nonzero=bool(bound[1]),socket_closed_after_probe=True,no_data_sent=True)))
finally:s.close()
