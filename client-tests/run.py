from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.environ.get('FOXFOX_WORKSPACE', str(ROOT.parent))).resolve()
SPEC = {'name':'ManaMetal-Beehive-Client', 'version':'1.0.0', 'modid':'manametalbeehiveclient', 'components':[{'tag':'buttons', 'probe':'ClientCheck', 'property':'beehiveclient'}]}
parser = argparse.ArgumentParser()
parser.add_argument('case', nargs='?', default='all', choices=['all'] + [c['tag'] for c in SPEC['components']])
parser.add_argument('--manametal', default='8.0.7', choices=['8.0.5','8.0.7'])
OPTIONS = parser.parse_args()
artifacts = [ROOT / 'dist' / (SPEC['name'] + '-1.7.10-' + SPEC['version'] + '.jar')]
ids = [SPEC['modid']]
for artifact in artifacts:
    if not artifact.is_file(): raise SystemExit('Build first: ' + str(artifact))


def run_case(case):
    fixture = ROOT / 'build' / ('client-' + OPTIONS.manametal)
    fixture.mkdir(parents=True, exist_ok=True)
    game = fixture / 'client'
    # Reset only this known isolated fixture; no live game or server directory is modified.
    if game.exists():
        resolved = game.resolve()
        if resolved.parent != fixture.resolve() or not resolved.is_relative_to((ROOT / 'build').resolve()):
            raise ValueError('Unexpected fixture path: ' + str(resolved))
        shutil.rmtree(resolved)
    mods = game / 'mods'
    mods.mkdir(parents=True)
    if 'manametalbeehiveclient' in ids:
        for name in ('config', 'falsepattern'):
            source = WORKSPACE / 'FoxFoxAccessories/test-server' / name
            if source.exists(): shutil.copytree(source, game / name, dirs_exist_ok=True)
    config = game / 'config'
    config.mkdir(exist_ok=True)
    (config / 'splash.properties').write_text('enabled=false\n', encoding='ascii')
    (game / 'options.txt').write_text('fullscreen:false\nlang:zh_CN\nguiScale:2\noverrideWidth:1280\noverrideHeight:720\n', encoding='ascii')
    # Mute the isolated test directory before starting any game client.
    sound_options = ''.join('soundCategory_' + c + ':0.0\n' for c in
                            ('master', 'music', 'record', 'weather', 'block', 'hostile', 'neutral', 'player', 'ambient'))
    with (game / 'options.txt').open('a', encoding='ascii') as options_file:
        options_file.write(sound_options)
    patterns = ['lwjgl3ify-*.jar', '+unimixins-*.jar', 'gtnhlib-*.jar', '*CodeChickenCore*.jar', 'NotEnoughItems-*.jar']
    if 'manametalbeehiveclient' in ids:
        patterns += ['*Muya*.jar']
    for pattern in patterns:
        matches = list((WORKSPACE / '.minecraft/mods').glob(pattern))
        if len(matches) != 1: raise SystemExit('Expected one dependency for ' + pattern)
        path = matches[0]
        shutil.copy2(path, mods / path.name.split(']', 1)[-1])
    mana = WORKSPACE / ('[魔法金属]manametalmod-8.0.5.jar' if OPTIONS.manametal == '8.0.5' else 'fcwqmmmserver/mods/manametalmod-8.0.7.jar')
    shutil.copy2(mana, mods / ('manametalmod-' + OPTIONS.manametal + '.jar'))
    (mods / '1.7.10').mkdir()
    for path in (WORKSPACE / '.minecraft/mods/1.7.10').glob('*.jar'):
        shutil.copy2(path, mods / '1.7.10' / path.name)
    for artifact in artifacts: shutil.copy2(artifact, mods / artifact.name)
    classes = fixture / 'probe-classes'
    if classes.exists():
        if classes.resolve().parent != fixture.resolve(): raise ValueError('Unexpected probe output')
        shutil.rmtree(classes.resolve())
    classes.mkdir()
    libs = WORKSPACE / '.minecraft/libraries'
    deps = [WORKSPACE / 'FoxFoxAccessories/tools/forge-1.7.10-srg.jar',
            *artifacts, *sorted(mods.glob('*.jar')), *sorted(libs.rglob('*.jar'))]
    subprocess.run(['javac', '--release', '8', '-Xlint:-options', '-encoding', 'UTF-8',
                    '-cp', os.pathsep.join(map(str, deps)), '-d', str(classes),
                    str(ROOT / 'client-tests' / (case['probe'] + '.java'))], check=True)
    with zipfile.ZipFile(mods / 'foxfox-test-probe.jar', 'w', zipfile.ZIP_DEFLATED) as jar:
        for path in sorted(classes.rglob('*.class')): jar.write(path, path.relative_to(classes).as_posix())
    profile_dir = WORKSPACE / 'fcwqmmmserver/deployment/java21'
    profile = json.loads((profile_dir / 'prepared-client-version.json').read_text('utf-8-sig'))
    cp = os.pathsep.join(json.loads((profile_dir / 'client-classpath.json').read_text('utf-8-sig')))
    natives = game / 'natives'
    natives.mkdir()
    args = ['-Xms256m', '-Xmx2G', '-XX:+UseG1GC', '-D' + case['property'] + '.test.root=' + str(fixture),
            '-Dfoxfox.test.mods=' + ','.join(ids)]
    args += [a.replace('${classpath}', cp).replace('${natives_directory}', str(natives))
             for a in profile['arguments']['jvm'] if isinstance(a, str)]
    args += [profile['mainClass'], '--username', 'FoxFoxTest', '--version', profile['id'],
             '--gameDir', str(game), '--assetsDir', str(WORKSPACE / '.minecraft/assets'), '--assetIndex', '1.7.10',
             '--uuid', '00000000000000000000000000000006', '--accessToken', '0', '--userProperties', '{}',
             '--userType', 'legacy', '--width', '1280', '--height', '720',
             '--tweakClass', 'cpw.mods.fml.common.launcher.FMLTweaker']
    argfile = fixture / 'client.args'
    argfile.write_text('\n'.join('"' + a.replace('\\', '\\\\').replace('"', '\\"') + '"' for a in args), encoding='utf-8')
    report = fixture / 'result.txt'
    report.write_text('RUNNING\n', encoding='utf-8')
    with (fixture / 'console.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen(['java', '@' + str(argfile)], cwd=game, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        print('Isolated client:', case['tag'], 'PID', process.pid, flush=True)
        try:
            code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
            raise SystemExit('Client timeout: ' + str(fixture / 'console.log'))
    result = report.read_text('utf-8')
    print(result, flush=True)
    if code != 0 or 'status=PASS' not in result:
        raise SystemExit('Client verification failed: ' + str(fixture / 'console.log'))
    record = {'status': 'PASS', 'case': case['tag'], 'manametal': OPTIONS.manametal,
              'artifacts': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts},
              'identityAndRegistration': 'PASS'}
    (fixture / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')


for case in SPEC['components']:
    if OPTIONS.case in ('all', case['tag']): run_case(case)
