import click, os, sys, shutil, json, six, hashlib, ssl

if sys.version_info[0] < 3:
    try:
        import contextlib
        import lzma
    except:
        try:
            from backports import lzma
        except:
            pass
import tarfile, zipfile

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

from six.moves.urllib import request

USE_SYMLINKS=(os.name == 'posix')

__CGET_DIR__ = os.path.dirname(os.path.realpath(__file__))

def cget_dir(*args):
    return os.path.join(__CGET_DIR__, *args)

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

def ensure_exists(f):
    if not f:
        raise BuildError("Invalid file path")
    if not os.path.exists(f):
        raise BuildError("File does not exists: " + f)

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

def get_app_dir(*args):
    return os.path.join(click.get_app_dir('cget'), *args)

def get_cache_path(*args):
    return get_app_dir('cache', *args)

def add_cache_file(key, f):
    mkdir(get_cache_path(key))
    shutil.copy2(f, get_cache_path(key, os.path.basename(f)))

def get_cache_file(key):
    p = get_cache_path(key)
    if os.path.exists(p):
        return os.path.join(p, next(ls(p)))
    else:
        return None

def delete_dir(path):
    if path is not None and os.path.exists(path): shutil.rmtree(path)

def symlink_dir(src, dst):
    for root, dirs, files in os.walk(src):
        for file in files:
            path = os.path.relpath(root, src)
            d = os.path.join(dst, path)
            mkdir(d)
            os.symlink(os.path.join(root, file), os.path.join(d, file))

def copy_dir(src, dst):
    for root, dirs, files in os.walk(src):
        for file in files:
            path = os.path.relpath(root, src)
            d = os.path.join(dst, path)
            mkdir(d)
            shutil.copy2(os.path.join(root, file), os.path.join(d, file))

def rm_symlink(file):
    if os.path.islink(file):
        f = os.readlink(file)
        if not os.path.exists(f): os.remove(file)

def rm_symlink_in(file, prefix):
    if os.path.islink(file):
        f = os.readlink(file)
        if f.startswith(prefix): 
            os.remove(file)

def rm_symlink_dir(d):
    for root, dirs, files in os.walk(d):
        for file in files:
            rm_symlink(os.path.join(root, file))

def rm_symlink_from(d, prefix):
    for root, dirs, files in os.walk(prefix):
        for file in files:
            rm_symlink_in(os.path.join(root, file), d)

def rm_dup_dir(d, prefix, remove_both=True):
    for root, dirs, files in os.walk(d):
        for file in files:
            fullpath = os.path.join(root, file)
            relpath = os.path.relpath(fullpath, d)
            if '..' in relpath: 
                raise BuildError('Trying to remove link outside of prefix directory: ' + relpath)
            os.remove(os.path.join(prefix, relpath))
            if remove_both: os.remove(fullpath)

def rm_empty_dirs(d):
    has_files = False
    for x in os.listdir(d):
        p = os.path.join(d, x)
        if os.path.isdir(p) and not os.path.islink(p): 
            has_files = has_files or rm_empty_dirs(p)
        else: 
            has_files = True
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

def download_to(url, download_dir, insecure=False):
    name = url.split('/')[-1]
    file = os.path.join(download_dir, name)
    click.echo("Downloading {0}".format(url))
    bar_len = 1000
    with click.progressbar(length=bar_len, width=70) as bar:
        def hook(count, block_size, total_size):
            percent = int(count*block_size*bar_len/total_size)
            if percent > 0 and percent < bar_len: 
                # Hack because we can't set the position
                bar.pos = percent
                bar.update(0)
        context = None
        if insecure: context = ssl._create_unverified_context()
        request.FancyURLopener(context=context).retrieve(url, filename=file, reporthook=hook, data=None)
        bar.update(bar_len)
    return file

def transfer_to(f, dst, copy=False):
    if USE_SYMLINKS and not copy: return symlink_to(f, dst)
    else: return copy_to(f, dst)

def retrieve_url(url, dst, copy=False, insecure=False, hash=None):
    remote = not url.startswith('file://')
    # Retrieve from cache
    if remote and hash:
        f = get_cache_file(hash.replace(':', '-'))
        if f: return f
    f = download_to(url, dst, insecure=insecure) if remote else transfer_to(url[7:], dst, copy=copy)
    if os.path.isfile(f) and hash:
        click.echo("Computing hash: {}".format(hash))
        if check_hash(f, hash): 
            if remote: add_cache_file(hash.replace(':', '-'), f)
        else:
            raise BuildError("Hash doesn't match for {0}: {1}".format(url, hash))
    return f

def extract_ar(archive, dst, *kwargs):
    if sys.version_info[0] < 3 and archive.endswith('.xz'):
        with contextlib.closing(lzma.LZMAFile(archive)) as xz:
            with tarfile.open(fileobj=xz, *kwargs) as f:
                f.extractall(dst)
    elif archive.endswith('.zip'):
        with zipfile.ZipFile(archive,'r') as f:
            f.extractall(dst)
    else:
        tarfile.open(archive, *kwargs).extractall(dst)

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

def yield_from(f):
    @six.wraps(f)
    def g(*args, **kwargs):
        return flat(f(*args, **kwargs))
    return g

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

def as_dict_str(d):
    result = {}
    for x in d:
        result[x] = str(d[x])
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
        cmd(c, env=as_dict_str(merge(self.env, self._get_paths_env(), env)), **kwargs)

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
