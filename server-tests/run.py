from pathlib import Path
import os
import shutil
import socket
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding='utf8')
root = Path(__file__).resolve().parents[1]
workspace = Path(os.environ.get('MANAMETAL_WORKSPACE', os.environ.get('FOXFOX_WORKSPACE', root.parent)))
version = sys.argv[1] if len(sys.argv) > 1 else '8.0.7'
assert version in ('8.0.5', '8.0.7')
fixture = root / ('build/server-' + version)
source = workspace / 'FoxFoxAccessories/test-server'
fixture.mkdir(parents=True, exist_ok=True)
for name in ('libraries', 'config', 'falsepattern'):
    if not (fixture / name).exists():
        shutil.copytree(source / name, fixture / name)
for name in ('Crucible-1.7.10-83c2ff2.jar', 'java21args.txt', 'eula.txt'):
    shutil.copy2(source / name, fixture / name)
mods = fixture / 'mods'
mods.mkdir(exist_ok=True)
for pattern in ('*Muya*.jar', 'lwjgl3ify-*.jar', '+unimixins-*.jar', 'gtnhlib-*.jar'):
    for p in (source / 'mods').glob(pattern):
        shutil.copy2(p, mods / p.name)
mana = workspace / ('[魔法金属]manametalmod-8.0.5.jar' if version == '8.0.5' else 'fcwqmmmserver/mods/manametalmod-8.0.7.jar')
shutil.copy2(mana, mods / ('manametalmod-' + version + '.jar'))
shutil.copy2(root / ('build/client-' + version + '/packet-cases.nbt'), fixture / 'packet-cases.nbt')
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
(fixture / 'server.properties').write_text('server-ip=127.0.0.1\nserver-port=' + str(port) + '\nonline-mode=false\n'
    'level-name=beehive-auto-fixture\nlevel-type=FLAT\ngenerator-settings=2;7,2x3,2;1;\n'
    'view-distance=2\nspawn-protection=0\nspawn-monsters=false\nspawn-animals=false\n'
    'generate-structures=false\nenable-query=false\nenable-rcon=false\nmax-players=1\nallow-nether=false\n', encoding='ascii')
classes = root / ('build/server-probe-' + version)
classes.mkdir(exist_ok=True)
deps = [workspace / 'FoxFoxAccessories/tools/forge-1.7.10-srg.jar',
        mods / ('manametalmod-' + version + '.jar'), *sorted((workspace / '.minecraft/libraries').rglob('*.jar'))]
subprocess.run(['javac', '--release', '8', '-Xlint:-options', '-encoding', 'UTF-8', '-cp', os.pathsep.join(map(str, deps)),
                '-d', str(classes), str(root / 'server-tests/ServerCheck.java')], check=True)
with zipfile.ZipFile(mods / 'beehive-packet-replay-test.jar', 'w', zipfile.ZIP_DEFLATED) as jar:
    for p in classes.rglob('*.class'):
        jar.write(p, p.relative_to(classes).as_posix())
report = fixture / 'result.txt'
if report.exists():
    report.unlink()
with (fixture / 'console.log').open('w', encoding='utf8') as log:
    proc = subprocess.Popen(['java', '-Xms512M', '-Xmx2G', '-noverify', '@java21args.txt',
                            '-Djava.awt.headless=true', '-Dbeehiveclient.server.root=' + str(fixture),
                            '-jar', 'Crucible-1.7.10-83c2ff2.jar', 'nogui'], cwd=fixture, stdin=subprocess.PIPE,
                            stdout=log, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    print('Isolated runtime', version, 'PID', proc.pid, 'port', port, flush=True)
    try:
        code = proc.wait(timeout=240)
    except subprocess.TimeoutExpired:
        proc.stdin.write(b'stop\n'); proc.stdin.flush()
        try:
            proc.wait(timeout=25)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait()
        raise SystemExit('Runtime timeout; inspect ' + str(fixture / 'console.log'))
print(report.read_text(encoding='utf8') if report.exists() else 'No probe report; exit=' + str(code))
if code != 0 or not report.exists() or 'status=PASS' not in report.read_text(encoding='utf8'):
    raise SystemExit(1)
