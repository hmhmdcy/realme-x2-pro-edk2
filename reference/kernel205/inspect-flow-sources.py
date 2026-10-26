from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
for name,terms in [('drivers/tty/serial/qcom_geni_serial.c',['MANUAL_RFR','set_mctrl(','set_termios(']),('drivers/bluetooth/hci_serdev.c',['set_flow_control','set_rts'])]:
 t=(k/name).read_text().splitlines();ix=[i for i,l in enumerate(t) if any(s in l for s in terms)]
 print(name+'\n'+'\n'.join(str(i+1)+':'+l for i,l in enumerate(t) if any(abs(i-n)<11 for n in ix)))
