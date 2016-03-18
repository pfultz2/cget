import click, os, sys, shutil, json, six

import tarfile

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

from six.moves.urllib import request

def is_string(obj):
    return isinstance(obj, six.string_types)

def quote(s):
    return json.dumps(s)

class BuildError(Exception):
    def __init__(self, msg=None):
        self.msg = msg
    def __str__(self):
        if None: return "Build failed"
        else: return self.msg

def can(f):
    try:
        f()
        return True
    except:
        return False

def try_until(*args):
    for arg in args[:-1]:
        try: 
            arg()
            return
        except:
            pass
    try:
        args[-1]()
    except:
        raise

def write_to(file, lines):
    content = list((line + "\n" for line in lines))
    if (len(content) > 0):
        with open(file, 'w') as f:
            f.writelines(content)

def mkdir(p):
    if not os.path.exists(p): os.makedirs(p)
    return p
    
def mkfile(d, file, content, always_write=True):
    mkdir(d)
    p = os.path.join(d, file)
    if not os.path.exists(p) or always_write:
        write_to(p, content)
    return p

def ls(p, predicate=lambda x:True):
    if os.path.exists(p):
        return (d for d in os.listdir(p) if predicate(os.path.join(p, d)))
    else:
        return []

def delete_dir(path):
    if path is not None and os.path.exists(path): shutil.rmtree(path)

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
            if percent > 0 and percent < 100: bar.update(percent)
        request.urlretrieve(url, filename=file, reporthook=hook, data=None)
    return file

def retrieve_url(url, dst):
    if url.startswith('file://'): return copy_to(url[7:], dst)
    else: return download_to(url, dst)

def extract_ar(archive, dst):
    tarfile.open(archive).extractall(dst)

def which(p, paths=None):
    exes = [p+x for x in ['', '.exe', '.bat']]
    for dirname in list(paths or [])+os.environ['PATH'].split(os.pathsep):
        for exe in exes:
            candidate = os.path.join(os.path.expanduser(dirname), exe)
            if os.path.exists(candidate):
                return candidate
    raise BuildError("Can't find file %s" % p)

def merge(*args):
    result = {}
    for d in args:
        result.update(dict(d or {}))
    return result

def cmd(args, env=None, **kwargs):
    child = subprocess.Popen(args, env=merge(os.environ, env), **kwargs)
    child.communicate()
    if child.returncode != 0: raise BuildError("Error: " + str(args))

def as_list(x):
    if is_string(x): return [x]
    else: return list(x)

class Commander:
    def __init__(self, paths=None, env=None, verbose=False):
        self.paths = paths
        self.env = env
        self.verbose = verbose

    def _get_paths_env(self):
        if self.paths is not None:
            return { 'PATH': os.pathsep.join(list(self.paths)+[os.environ['PATH']]) }
        else: return None

    def _cmd(self, name, args=None, options=None, env=None, **kwargs):
        exe = which(name, self.paths)
        option_args = ["{0}={1}".format(key, value) for key, value in six.iteritems(options or {})]
        c = [exe] + option_args + as_list(args or [])
        if self.verbose: click.secho(' '.join(c), bold=True)
        cmd(c, env=merge(self.env, self._get_paths_env(), env), **kwargs)

    def __getattr__(self, name):
        c = name.replace('_', '-')
        def f(*args, **kwargs):
            self._cmd(c, *args, **kwargs)
        return f

