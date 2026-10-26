from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
text=(ref/'test-sensor-ram-v11.sh').read_text()
text=text.replace('k113-reboot-audio-clean-7/','k113-reboot-audio-clean-8/')
text=text.replace('ram-v11','ram-v12').replace('RAM_V11','RAM_V12')
start=text.index('sleep 20\nprintf')
end=text.index('cat "$node/state" > "$dest/slpi-state-after.txt"',start)
text=text[:start]+'''# Capture early NPA client creation before later requests overwrite its ring.
sleep 3
kill -0 "$owner"
printf 'SKIPPED_FOR_EARLY_CAPTURE\\n' > "$dest/query-exit.txt"
cat /proc/uptime > "$dest/early-capture-uptime.txt"
printf 'EARLY_ULOG_CAPTURE_WITHOUT_SSC_QUERIES\\n'
'''+text[end:]
(ref/'test-sensor-ram-v12.sh').write_text(text)
clean=(ref/'quiesce-clean-boot6.sh').read_text()
clean=clean.replace('k113-reboot-audio-clean-6/','k113-reboot-audio-clean-7/')
(ref/'quiesce-clean-boot7.sh').write_text(clean)
print('V12_EARLY_NO_QUERY_CAPTURE_AND_BOOT7_QUIESCE_PREPARED')
