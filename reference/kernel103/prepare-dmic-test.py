from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel103'
s=(ref/'test-capture.sh').read_text().replace('k103-capture','k103-capture-dmic0')
s=s.replace('AMIC MUX0','DMIC MUX5').replace("'DMIC MUX5' ADC1","'DMIC MUX5' DMIC0")
s=s.replace('ADC MUX0','ADC MUX5').replace("'ADC MUX5' AMIC","'ADC MUX5' DMIC")
s=s.replace('CDC_IF TX0 MUX','CDC_IF TX5 MUX').replace("'CDC_IF TX5 MUX' DEC0","'CDC_IF TX5 MUX' DEC5")
s=s.replace('AIF1_CAP Mixer SLIM TX0','AIF1_CAP Mixer SLIM TX5')
assert not (ref/'test-capture-dmic0.sh').exists()
(ref/'test-capture-dmic0.sh').write_text(s)
print('DMIC0_TX5_CONTRACT_TEST_PREPARED')
