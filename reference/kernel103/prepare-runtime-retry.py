from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel103';out=Path('/mnt/e/edk2-samurai-out/kernel103')
source=(ref/'collect-audio-runtime.sh').read_text().replace('/tmp/k103-audio-runtime','/tmp/k103-audio-runtime-retry1').replace('k103-audio-runtime\n','k103-audio-runtime-retry1\n')
source=source.replace('test ! -r "$f" || cat "$f" > "$dir/native-api.txt"', '''if test -r "$f"; then
        if cat "$f" > "$dir/native-api.txt" 2> "$dir/native-api-error.txt"; then
            echo 0 > "$dir/native-api-exit.txt"
        else
            echo 1 > "$dir/native-api-exit.txt"
        fi
    fi''')
assert not (ref/'collect-audio-runtime-retry1.sh').exists()
(ref/'collect-audio-runtime-retry1.sh').write_text(source)
print('RETAINED_FIRST_API_FAILURE; RETRY_COLLECTOR_RECORDS_QUERY_EXIT')
