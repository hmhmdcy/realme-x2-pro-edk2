from pathlib import Path
import subprocess
here = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel207/block-rollover')
src = (here.parent / 'kernel206/test-tftp-qrtr.c').read_text().replace('instance == 206', 'instance == 207').replace('samurai-validation206', 'samurai-validation207')
src = src.replace('static unsigned int transactions, compared_bytes;', 'static unsigned int transactions, compared_bytes, wrap_events;\nstatic int duplicate_ack, duplicate_uncommitted, duplicate_committed;')
src = src.replace('alarm(30)', 'alarm(60)')
src = src.replace('        send_packet(fd, &peer, packet, payload + 4);\n        offset += payload;', '''        send_packet(fd, &peer, packet, payload + 4);
        if (!(uint16_t)block) wrap_events++;
        if (duplicate_uncommitted && block == 1 && window > 1) {
            send_packet(fd, &peer, packet, payload + 4);
            duplicate_uncommitted = 0;
        }
        offset += payload;''')
needle = '            assert(get16(packet) == 4 && get16(packet + 2) == block);'
assert src.count(needle) == 1
src = src.replace(needle, '''            if (!(get16(packet) == 4 && get16(packet + 2) == (uint16_t)block))
                fprintf(stderr, "WRQ_ACK_MISMATCH absolute=%u received=%u expected=%u\\n", block, get16(packet + 2), (uint16_t)block);
            assert(get16(packet) == 4 && get16(packet + 2) == (uint16_t)block);
            if (duplicate_committed) {
                put16(packet, 3); put16(packet + 2, block);
                memcpy(packet + 4, data + offset - payload, payload);
                send_packet(fd, &peer, packet, payload + 4);
                got = receive(fd, packet, sizeof(packet), &response);
                assert(got == 4 && get16(packet) == 4 && get16(packet + 2) == (uint16_t)block);
                duplicate_committed = 0;
            }''')
src = src.replace('if (options) { assert(get16(packet) == 6); ack(fd, &peer, 0); }', 'if (options) { assert(get16(packet) == 6); ack(fd, &peer, 0); if (duplicate_ack) { ack(fd, &peer, 0); duplicate_ack = 0; } }')
src = src.replace('get16(packet + 2) == block);', 'get16(packet + 2) == (uint16_t)block);')
src = src.replace('        assert(!memcmp(packet + 4, expected + offset, payload)); offset += payload;', '''        if (memcmp(packet + 4, expected + offset, payload))
            fprintf(stderr, "RRQ_DATA_MISMATCH absolute=%u offset=%zu\\n", block, offset);
        assert(!memcmp(packet + 4, expected + offset, payload)); offset += payload;
        if (!(uint16_t)block) wrap_events++;''')
src = src.replace('    } else {\n        assert(!strcmp(argv[2], "pass"));', '''    } else if (!strcmp(argv[2], "rollover-write") || !strcmp(argv[2], "rollover-read") || !strcmp(argv[2], "rollover")) {
        size_t count = !strcmp(argv[2], "rollover") ? 1048603 : 524305;
        unsigned char *large = malloc(count); assert(large);
        for (size_t i = 0; i < count; i++) large[i] = (unsigned char)(i * 29 + (i >> 16) * 37 + 7);
        unsigned int window = !strcmp(argv[2], "rollover-read") ? 1 : 7;
        write_file(path, large, count, 8, window, 0, 1, 0);
        read_file(path, large, count, 8, 7, 0, 1, 0);
        free(large);
    } else {
        assert(!strcmp(argv[2], "pass"));
        duplicate_uncommitted = duplicate_committed = 1;''')
src = src.replace('        read_file(path, data, 6145, 1024, 4, 0, 1, 0);', '''        read_file(path, data, 6145, 1024, 4, 0, 1, 0);
        duplicate_ack = 1;
        read_file(path, data, 6145, 1024, 4, 0, 1, 0);''')
src = src.replace('\\"instance\\":%u}\\n", transactions, compared_bytes, instance);', '\\"instance\\":%u,\\"wire_block_zero_events\\":%u}\\n", transactions, compared_bytes, instance, wrap_events);')
assert 'wire_block_zero_events' in src
path = here / 'test-tftp-qrtr.c'; path.write_text(src)
base = Path('/mnt/e/edk2-samurai-out/kernel206/tftp-clean-rebuild-r2/qrtr')
p = subprocess.run(['aarch64-linux-gnu-gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-I' + str(base / 'include'), str(path), str(base / 'lib/qrtr.c'), str(base / 'lib/logging.c'), '-o', str(out / 'native-client')], capture_output=True)
(out / 'native-client-build.log').write_bytes(p.stdout + p.stderr)
assert p.returncode == 0 and not p.stderr, p.stderr.decode()
print('Native client built: nonperiodic payload, two wire rollovers, duplicate DATA and ACK cases.')
