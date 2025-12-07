import os
import time
import subprocess

# A simple test to verify startup and uvicorn logs are rotated
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(PROJECT_ROOT, 'backend', 'logs')
STARTUP_LOG = os.path.join(LOG_DIR, 'startup.log')
UVI_LOG = os.path.join(LOG_DIR, 'uvicorn.log')

def run(cmd):
    print('RUN:', cmd)
    subprocess.check_call(cmd, shell=True)

# Make sure logs dir exists
os.makedirs(LOG_DIR, exist_ok=True)

# create large files to trigger rotation
with open(STARTUP_LOG, 'wb') as f:
    f.write(b'0' * 6000000)
with open(UVI_LOG, 'wb') as f:
    f.write(b'0' * 6000000)

print('Wrote large startup and uvicorn logs to trigger rotation.')

# restart backend
run('docker compose -f .\compose.yaml restart backend')

# wait a bit for entrypoint daemon to run one rotation cycle
print('Waiting 10 seconds for rotation to occur...')
time.sleep(10)

# list rotated files
rotated = [p for p in os.listdir(LOG_DIR) if p.endswith('.log.gz')]
print('Rotated files:', rotated)

if any('startup-' in r for r in rotated) and any('uvicorn-' in r for r in rotated):
    print('Rotation test passed')
    exit(0)
else:
    print('Rotation test failed')
    exit(2)
