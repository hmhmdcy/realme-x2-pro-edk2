from pathlib import Path
import host

target=host.PRIVATE/'first-debug-worker-error-private.txt'
host.download('/var/lib/samurai/k208-debug-nmea/worker-error-private.txt',target)
print(target.read_text())
