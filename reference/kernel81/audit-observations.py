from pathlib import Path
import gzip,hashlib,json,re,subprocess
w=Path('/mnt/e/RealmeX2Pro edk2');ref=w/'reference/kernel81';out=Path('/mnt/e/edk2-samurai-out/kernel81');linux=Path('/home/cy122/x2pro-linux/linux')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes={}
for row in (out/'device-hashes.txt').read_text().splitlines():
    digest,name=row.split('  ',1);name=Path(name).name.removeprefix('k81-');assert sha(out/name)==digest;hashes[name]=digest
assert gzip.decompress((out/'final-dmesg.txt.gz').read_bytes())==(out/'final-dmesg.txt').read_bytes()
s=(out/'stock-state.txt').read_text();values={}
for name,opcode,size in [('stock_seal_state',0x54,4),('stock_gauge_enabled',0x57,2)]:
    b=bytes.fromhex(re.search(name+r' command=0x[0-9a-f]+ request=[0-9a-f]+ response=([0-9a-f]{72})',s)[1])
    assert b[:2]==bytes((opcode,0)) and b[35]==size+4 and b[34]==(255-sum(b[:b[35]-2]))&255
    short=bytes.fromhex(re.search(name+r' stock_four_bytes=([0-9a-f]{8})',s)[1]);assert short==b[:4]
    values[name]={'opcode':hex(opcode),'payload_hex':b[2:2+size].hex(),'payload_unsigned_le':int.from_bytes(b[2:2+size],'little'),'length':b[35],'checksum':hex(b[34]),'checksum_echo_length_and_stock_short_read_match':True}
assert values['stock_seal_state']['payload_unsigned_le']==0x386 and values['stock_gauge_enabled']['payload_unsigned_le']==0x18
assert 'session80_exact_identity_and_firmware_guard=PASS' in s and 'query_rc=0' in s
assert 'guard_mp_rc=2' in s and 'guard_touch_rc=2' in s
stock=(out/'stock-temperatures.txt').read_text();words={}
for name,sel in [('Temperature',6),('InternalTemperature',0x28),('PackVoltage',8),('InstantCurrent',0x0c),('AverageCurrent',0x14)]:
    b=bytes.fromhex(re.search(name+rf' selector=0x{sel:02x} bytes=([0-9a-f]{{4}})',stock)[1]);words[name]=int.from_bytes(b,'little')
assert words=={'Temperature':3037,'InternalTemperature':3025,'PackVoltage':8638,'InstantCurrent':65533,'AverageCurrent':0}
assert all(p in stock for p in ('guard_mp_rc=2','guard_touch_rc=2','read_rc=0','MAC_requests=0 register_data_writes=0'))
regs=dict(re.findall(r'reg=(0x[0-9a-f]{2}) value=(0x[0-9a-f]{2})',(out/'final-registers.txt').read_text()))
expected={'0x08':'0x16','0x09':'0x4c','0x0a':'0x36','0x07':'0x14','0x00':'0x12','0x01':'0x2d','0x02':'0x06','0x03':'0xa2','0x04':'0x68','0x0f':'0x12','0x0b':'0x00','0x13':'0x0f'}
assert regs==expected
state=(out/'final-state.txt').read_text();assert state.splitlines()[0]=='87753933-4992-45d2-aaf5-d9db9c11d1a3' and state.splitlines()[3]=='0'
dmesg=(out/'final-dmesg.txt').read_text();patterns=('dsi.*(?:error|underflow|overflow)',r'\bOops:',r'\bBUG:','smmu.*(?:fault|error)','geni.*(?:error|failed)','i2c.*(?:error|failed)')
issues={p:len(re.findall(p,dmesg,re.I)) for p in patterns};assert not any(issues.values()),issues
assert [int(x) for x in re.findall(r'underrun:\s*(\d+)',state)]==[0]
frame_timeouts=len(re.findall(r'frame done timeout',dmesg,re.I))
assert frame_timeouts==2
assert re.search(r'frame_done_cnt:2mode:',state)
image=sha(linux/'arch/arm64/boot/Image');config=sha(linux/'.config')
assert image=='f90e6807bad34db3f3c88206ec952b0de78775272e407eb525ea2440ded476bb' and config=='9d9f10ae4a96e4a0575b7c51d818180a68e596e84898a3849fe1183307223c6d'
assert '# CONFIG_BATTERY_BQ27XXX_DT_UPDATES_NVM is not set' in (linux/'.config').read_text()
for row in (w/'reference/kernel78/display-source-hashes.txt').read_text().splitlines():
    digest,name=row.split('  ',1);assert sha(linux/name)==digest
readers={name:{'source_sha256':sha(ref/(name+'.c')),'binary_sha256':sha(out/name),'bytes':(out/name).stat().st_size} for name in ('read-stock-gauge-state','read-stock-temperatures')}
vendor_hash='33284b6ebb2f9829f04338733a76169ce1cd7c98f3a4c4413ed832bea20abd56';modem_hash='88af46265a4f23c634b2a3c0a4be6815caf796f4b3bb398a6223a565c9e132f0'
inventory=(out/'firmware-inventory.txt').read_text();extraction=(out/'wifi-extraction.txt').read_text()
assert inventory.count(vendor_hash)==2 and inventory.count(modem_hash)==2 and extraction.count(modem_hash)==2
assert '/tmp/k81-vendor-ro ext4 ro,relatime,norecovery' in inventory and '/tmp/k81-modem-ro vfat ro,' in inventory
assert 'PASS source partitions unmounted' in inventory and 'source partition hash unchanged and unmounted' in extraction
result={'trusted_user_battery_history':'never replaced','battery_identity_not_inferred_from_history':True,'device_captures_sha256_verified':hashes,'stock_state_responses':values,'exact_legacy_extended_and_FW_guard_passed':True,'stock_sealed_bits':3,'stock_gauge_enable_bit':1,'other_TI_bit_decodes_are_tentative_for_2719':True,'standard_word_values':words,'temperature_C_if_0p1K':30.55,'internal_temperature_C_if_0p1K':29.35,'thermistor_wiring_calibration_protection_not_validated':True,'MAC_requests':4,'new_standard_word_combined_reads':5,'full_session80_status_prototype_run':False,'SafetyStatus_PFStatus_DAStatus2_queries':0,'configuration_NVM_OTP_FET_reset_unseal_writes':0,'device_partition_writes':0,'MP2650_current_readback_unchanged_from_79':regs,'boot_id':state.splitlines()[0],'final_uptime_seconds':float(state.splitlines()[2].split()[0]),'final_taint':0,'final_voltage_uV':8639000,'final_temperature_deciC':306,'final_average_current_uA':0,'log_pattern_counts':issues,'frame_done_timeout_count':frame_timeouts,'frame_done_timeouts_unresolved':True,'kernel_image_sha256':image,'kernel_config_sha256':config,'current_dtb_sha256':sha(linux/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'),'display_source_hashes_preserved':True,'readers':readers,'vendor_partition_hash_before_after_identical':vendor_hash,'modem_partition_hash_before_after_identical':modem_hash,'firmware_archive_private_not_installed':True,'wireless_and_remote_processors_unchanged_disabled':True,'no_new_optical_or_GPU_test':True,'capture_preceded_additional_display_probe':True}
(ref/'observation-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS capture hashes, fixed stock R responses, temperature words, unchanged MP2650/Image/config/display source, source partition hashes and unmounts; final uptime',result['final_uptime_seconds'],'selected log patterns',issues,'unresolved frame-done timeouts',frame_timeouts)
