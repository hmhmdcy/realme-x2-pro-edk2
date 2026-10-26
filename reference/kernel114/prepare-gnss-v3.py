from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114')
text=(ref/'gnss-single-client-v2.py').read_text().replace('k114-gnss-single-client-v2','k114-gnss-single-client-v3').replace('116','117')
text=text.replace('Qmi.LocFixRecurrenceType.PERIODIC)','Qmi.LocFixRecurrenceType.PERIODIC_FIXES)')
for key in ['stop_ack','start_ack','client_registered']:
    text=text.replace(f"state['{key}']=bool(output.get_result())",f"output.get_result()  # GI raises on protocol failure; returns None on success.\n    state['{key}']=True")
(ref/'gnss-single-client-v3.py').write_text(text)
text=(ref/'probe-gnss-single-client-v2.sh').read_text().replace('k114-gnss-single-client-v2','k114-gnss-single-client-v3').replace('116','117')
(ref/'probe-gnss-single-client-v3.sh').write_text(text)
print('GNSS117_CORRECT_GI_RESULT_AND_RECURRENCE_PREPARED')
