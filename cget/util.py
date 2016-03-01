import click, os, urllib, sys

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

def write_to(file, lines):
    content = list((line + "\n" for line in lines))
    if (len(content) > 0):
        open(file, 'w').writelines(content)

def mkdir(p):
    if not os.path.exists(p): os.makedirs(p)
    return p
    
def mkfile(d, file, content, always_write=True):
    mkdir(d)
    p = os.path.join(d, file)
    if not os.path.exists(p) or always_write:
        write_to(p, content)
    return p

def lsdir(p):
    return (d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d)))

def symlink_dir(src, dst):
    for root, dirs, files in os.walk(src):
        for file in files:
            path = os.path.relpath(root, src)
            d = os.path.join(dst, path)
            mkdir(d)
            os.symlink(os.path.join(root, file), os.path.join(d, file))

def rm_symlink(file):
    if os.path.islink(file):
        f = os.readlink(file)
        if not os.path.exists(f): os.remove(file)

def rm_symlink_dir(d):
    for root, dirs, files in os.walk(d):
        for file in files:
            rm_symlink(os.path.join(root, file))

def rm_empty_dirs(d):
    has_files = False
    for x in os.listdir(d):
        p = os.path.join(d, x)
        if os.path.isdir(p): has_files = has_files or rm_empty_dirs(p)
        else: has_files = True
    if not has_files: os.rmdir(d)
    return has_files

def get_dirs(d):
    return (os.path.join(d,o) for o in os.listdir(d) if os.path.isdir(os.path.join(d,o)))

def download_to(url, download_dir):
    name = url.split('/')[-1]
    file = os.path.join(download_dir, name)
    click.echo("Downloading {0}".format(url))
    with click.progressbar(length=100) as bar:
        def hook(count, block_size, total_size):
            percent = int(count*block_size*100/total_size)
            if percent > 100: percent = 100
            if percent < 0: percent = 0
            bar.update(percent)
        urllib.urlretrieve(url, filename=file, reporthook=hook, data=None)
    return file

def cmake(args, cwd=None, toolchain=None, env=None):
    cmake_exe = ['cmake']
    if toolchain is not None: cmake_exe.append('-DCMAKE_TOOLCHAIN_FILE={0}'.format(toolchain))
    return subprocess.Popen(cmake_exe+list(args), cwd=cwd, env=None).communicate()


def pkg_config(args, path=None):
    pkg_config_exe = ['pkg-config']
    env = {}
    if path is not None: env['PKG_CONFIG_PATH'] = path
    return subprocess.Popen(pkg_config_exe+list(args), env=env).communicate()

