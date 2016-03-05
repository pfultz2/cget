import click, os, sys, shutil

import tarfile

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

if os.name == 'posix' and sys.version_info[0] < 3:
    import urllib
else:
    import urllib.request as urllib

def is_string(obj):
    return isinstance(obj, basestring)

def as_bytes(s):
    if sys.version_info[0] < 3: return bytes(s)
    else: return bytes(s, "UTF-8")

def as_string(x):
    if x is None: return ''
    elif sys.version_info[0] < 3: return str(x)
    else: return str(x, encoding="UTF-8")

class BuildError(Exception):
    def __init__(self, msg=None):
        self.msg = msg
    def __str__(self):
        if None: return "Build failed"
        else: return self.msg

def require(b):
    if not b: raise BuildError()

def requires(*args):
    for arg in args:
        require(arg())

def try_until(*args):
    for arg in args:
        if arg(): return True
    raise BuildError()

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
    if os.path.exists(p):
        return (d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d)))
    else:
        return []

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

def copy_to(src, dst_dir):
    target = os.path.join(dst_dir, os.path.basename(src))
    if os.path.isfile(src): shutil.copyfile(src, target)
    else: shutil.copytree(src, target)
    return target

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

def retrieve_url(url, dst):
    if url.startswith('file://'): return copy_to(url[7:], dst)
    else: return download_to(url, dst)

def extract_ar(a, d):
    tarfile.open(a).extractall(d)

def join_args(args):
    if is_string(args): return args
    else: return ' '.join(args)

def as_shell(args):
    if os.name == 'posix': return [join_args(args)]
    else: return args

def cmd(args, **kwargs):
    child = subprocess.Popen(as_shell(args), shell=True, **kwargs)
    child.communicate()
    return child.returncode == 0

def cmake(args, cwd=None, toolchain=None, env=None):
    cmake_exe = ['cmake']
    if toolchain is not None: cmake_exe.append('-DCMAKE_TOOLCHAIN_FILE={0}'.format(toolchain))
    return cmd(cmake_exe+list(args), cwd=cwd, env=env)


def pkg_config(args, path=None):
    pkg_config_exe = ['pkg-config']
    env = {}
    if path is not None: env['PKG_CONFIG_PATH'] = path
    return cmd(pkg_config_exe+list(args), env=env)

