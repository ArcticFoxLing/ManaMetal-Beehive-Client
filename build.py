from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import zipfile

root = Path(__file__).resolve().parent
workspace = Path(os.environ.get('MANAMETAL_WORKSPACE', os.environ.get('FOXFOX_WORKSPACE', root.parent)))
build = root / 'build'
classes = build / 'classes'
dist = root / 'dist'
if classes.exists():
    assert classes.resolve().parent == build.resolve()
    shutil.rmtree(classes)
classes.mkdir(parents=True)
dist.mkdir(exist_ok=True)
deps = [workspace / 'FoxFoxAccessories/tools/forge-1.7.10-srg.jar',
        workspace / 'fcwqmmmserver/mods/manametalmod-8.0.7.jar']
subprocess.run(['javac', '--release', '8', '-encoding', 'UTF-8', '-cp', os.pathsep.join(map(str, deps)),
                '-d', str(classes), *map(str, sorted((root / 'src').rglob('*.java')))], check=True)
artifact = dist / 'ManaMetal-Beehive-Client-1.7.10-1.0.0.jar'
with zipfile.ZipFile(artifact, 'w', zipfile.ZIP_DEFLATED) as jar:
    jar.write(root / 'LICENSE', 'META-INF/LICENSE')
    jar.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\r\n\r\n')
    for path in sorted(classes.rglob('*.class')):
        assert int.from_bytes(path.read_bytes()[6:8], 'big') == 52
        jar.write(path, path.relative_to(classes).as_posix())
    for path in sorted((root / 'src').rglob('*')):
        if path.is_file() and path.suffix != '.java':
            jar.write(path, path.relative_to(root / 'src').as_posix())
report = {'artifact': artifact.name, 'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
          'minecraft': '1.7.10', 'javaTarget': 8, 'clientOnly': True, 'coremod': False,
          'network': 'vanilla C0EPacketClickWindow only'}
(build / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print(json.dumps(report, indent=2))
