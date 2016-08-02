import click, os, sys, shutil, json, six, hashlib

if sys.version_info[0] < 3:
    try:
        import contextlib
        import lzma
    except:
        pass
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
    def __init__(self, msg=None, data=None):
        self.msg = msg
        self.data = data
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

def symlink_to(src, dst_dir):
    target = os.path.join(dst_dir, os.path.basename(src))
    os.symlink(src, target)
    return target

def download_to(url, download_dir):
    name = url.split('/')[-1]
    file = os.path.join(download_dir, name)
    click.echo("Downloading {0}".format(url))
    with click.progressbar(length=100) as bar:
        def hook(count, block_size, total_size):
            percent = int(count*block_size*100/total_size)
            if percent > 0 and percent < 100: bar.update(percent)
        request.FancyURLopener().retrieve(url, filename=file, reporthook=hook, data=None)
    return file

def retrieve_url(url, dst):
    if url.startswith('file://'): return symlink_to(url[7:], dst)
    else: return download_to(url, dst)

def extract_ar(archive, dst):
    if sys.version_info[0] < 3 and archive.endswith('.xz'):
        with contextlib.closing(lzma.LZMAFile(archive)) as xz:
            with tarfile.open(fileobj=xz) as f:
                f.extractall(dst)
    else: tarfile.open(archive).extractall(dst)

def hash_file(f, t):
    h = hashlib.new(t)
    h.update(open(f, 'rb').read())
    return h.hexdigest()

def check_hash(f, hash):
    t, h = hash.lower().split(':')
    return hash_file(f, t) == h

def which(p, paths=None, throws=True):
    exes = [p+x for x in ['', '.exe', '.bat']]
    for dirname in list(paths or [])+os.environ['PATH'].split(os.pathsep):
        for exe in exes:
            candidate = os.path.join(os.path.expanduser(dirname), exe)
            if os.path.exists(candidate):
                return candidate
    if throws: raise BuildError("Can't find file %s" % p)
    else: return None

def merge(*args):
    result = {}
    for d in args:
        result.update(dict(d or {}))
    return result

def flat(*args):
    for arg in args:
        for x in arg:
            for y in x: yield y

def cmd(args, env=None, **kwargs):
    e = merge(os.environ, env)
    child = subprocess.Popen(args, env=e, **kwargs)
    child.communicate()
    if child.returncode != 0: 
        raise BuildError(msg='Command failed: ' + str(args), data=e)

def as_list(x):
    if is_string(x): return [x]
    else: return list(x)

def to_define_dict(xs):
    result = {}
    for x in xs:
        if '=' in x:
            p = x.split('=')
            result[p[0]] = p[1]
        else:
            result[x] = ''
    return result

def actual_path(path, start=None):
    return os.path.normpath(os.path.join(start or os.getcwd(), os.path.expanduser(path)))

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

    def __getitem__(self, name):
        def f(*args, **kwargs):
            self._cmd(name, *args, **kwargs)
        return f

    def __contains__(self, name):
        exe = which(name, self.paths, throws=False)
        return exe is not None
