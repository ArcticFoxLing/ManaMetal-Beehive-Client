from pathlib import Path
import hashlib
import json
import shutil
import zipfile

root = Path(__file__).resolve().parent
dist = root / 'dist'
report = json.loads((root / 'build/verification.json').read_text(encoding='utf8'))
artifact = dist / report['artifact']
assert hashlib.sha256(artifact.read_bytes()).hexdigest() == report['sha256']
for version in ('8.0.5', '8.0.7'):
    client = root / ('build/client-' + version)
    verification = json.loads((client / 'verification.json').read_text(encoding='utf8'))
    assert verification['status'] == 'PASS'
    assert verification['artifacts'][artifact.name] == report['sha256']
    for side in ('client', 'server'):
        fixture = root / ('build/' + side + '-' + version)
        result = (fixture / 'result.txt').read_text(encoding='utf8')
        assert 'status=PASS' in result and 'status=FAIL' not in result
        shutil.copy2(fixture / 'result.txt', dist / (side + '-' + version + '.txt'))
        report.setdefault('validation', {})[side + '-' + version] = 'PASS'
shutil.copy2(root / '使用说明.md', dist / '使用说明.md')
shutil.copy2(root / 'build/client-8.0.7/screenshots/beehive-buttons.png', dist / '蜂箱按钮.png')
(dist / 'SHA256.txt').write_text(report['sha256'] + '  ' + artifact.name + '\n', encoding='ascii')
(dist / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf8')
with zipfile.ZipFile(dist / 'ManaMetal-Beehive-Client-1.7.10-1.0.0.zip', 'w', zipfile.ZIP_DEFLATED) as bundle:
    bundle.write(root / 'LICENSE', 'LICENSE')
    bundle.write(root / 'README.md', 'README.md')
    bundle.write(root / 'LICENSE', 'source/LICENSE')
    bundle.write(root / 'README.md', 'source/README.md')
    bundle.write(root / '.gitignore', 'source/.gitignore')
    bundle.write(root / '.gitattributes', 'source/.gitattributes')
    for path in sorted(dist.iterdir()):
        if path.suffix != '.zip' and path.is_file(): bundle.write(path, path.name)
print(json.dumps(report, indent=2))
