import base64, copy, argparse, six

def encode_url(url):
    x = six.b(url[url.find('://')+3:])
    return '_url_' + base64.urlsafe_b64encode(x).decode('utf-8').replace('=', '_')

def decode_url(url):
    s = url.replace('_', '=')[5:]
    return base64.urlsafe_b64decode(str(s)).decode('utf-8')

class PackageSource:
    def __init__(self, name=None, url=None, fname=None):
        self.name = name
        self.url = url
        self.fname = fname

    def to_name(self):
        if self.name is not None: return self.name
        if self.url is not None: return self.url
        return self.to_fname()

    def to_fname(self):
        if self.fname is None: self.fname = self.get_encoded_name_url()
        return self.fname

    def get_encoded_name_url(self):
        if self.name is None: return encode_url(self.url)
        else: return self.name.replace('/', '__')

    def get_src_dir(self):
        if self.url.startswith('file://'):
            return self.url[7:] # Remove "file://"
        raise TypeError()


def fname_to_pkg(fname):
    if fname.startswith('_url_'): return PackageSource(name=decode_url(fname), fname=fname)
    else: return PackageSource(name=fname.replace('__', '/'), fname=fname)

class PackageBuild:
    def __init__(self, pkg_src=None, define=None, parent=None, test=False, hash=None, build=None, cmake=None):
        self.pkg_src = pkg_src
        self.define = define or []
        self.parent = parent
        self.test = test
        self.build = build
        self.hash = hash
        self.cmake = cmake

    def merge(self, define):
        result = copy.copy(self)
        result.define.extend(define)
        return result

    def of(self, parent):
        result = copy.copy(self)
        result.parent = parent.to_fname()
        result.define.extend(parent.define)
        return result

    def to_fname(self):
        if isinstance(self.pkg_src, PackageSource): return self.pkg_src.to_fname()
        else: return self.pkg_src

    def to_name(self):
        if isinstance(self.pkg_src, PackageSource): return self.pkg_src.to_name()
        else: return self.pkg_src

def parse_pkg_build_tokens(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('pkg_src')
    parser.add_argument('-D', '--define', nargs='+')
    parser.add_argument('-H', '--hash')
    parser.add_argument('-X', '--cmake')
    parser.add_argument('-t', '--test', action='store_true')
    parser.add_argument('-b', '--build', action='store_true')
    return parser.parse_args(args=args, namespace=PackageBuild())

