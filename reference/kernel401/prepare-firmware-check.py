"""Reuse the full native/HAL firmware differential with Gamma-enabled pages."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel399/check-firmware-parcel.py').read_text().replace('stage=399','stage=401')
s=s.replace('lib.camss_a5_ipe_encode_colour_iq.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p];lib.camss_a5_ipe_encode_colour_iq.restype=ctypes.c_int','lib.camss_a5_ipe_encode_gamma_iq.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p];lib.camss_a5_ipe_encode_gamma_iq.restype=ctypes.c_int')
s=s.replace("raw=(P/'colour-input-private.bin').read_bytes();records=[raw[i:i+102] for i in range(0,len(raw),102)]","raw=(P/'gamma-input-private.bin').read_bytes();records=[raw[i:i+3174] for i in range(0,len(raw),3174)]")
s=s.replace("colour=ctypes.create_string_buffer(record[:46]+bytes(2)+record[46:]);out=ctypes.create_string_buffer(2860)","colour=ctypes.create_string_buffer(record[:46]+bytes(2)+record[46:102]);gamma=ctypes.create_string_buffer(record[102:]);out=ctypes.create_string_buffer(6016)")
s=s.replace('lib.camss_a5_ipe_encode_colour_iq(out,2860,r.f.DATA+0x40000,colour)','lib.camss_a5_ipe_encode_gamma_iq(out,6016,r.f.DATA+0x40000,colour,gamma)')
s=s.replace('m.u.mem_read(r.f.DATA+0x40000,2860)','m.u.mem_read(r.f.DATA+0x40000,6016)')
s=s.replace('arrays_and_cst_cc_cv_commands_within_existing_iq_page=True','typed_gamma_and_colour_commands_and_luts_in_retained_iq_region=True,gamma_iq_bytes=6016,iq_allocation_bytes=8192,gamma_program_type12_and_generic20=True')
s=s.replace("modules=mask,same_page_actual_c_region_accepted=True","modules=mask,gamma_enabled=True,retained_actual_c_region_accepted=True")
(HERE/'check-firmware-parcel.py').write_text(s)
print('Prepared full Gamma-enabled firmware/native striping differential.')
