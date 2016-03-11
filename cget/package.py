import base64

import cget.util as util


def encode_url(url):
    x = url[url.find('://')+3:]
    return '_url_' + util.as_string(base64.urlsafe_b64encode(util.as_bytes(x))).replace('=', '_')

def decode_url(url):
    return base64.urlsafe_b64decode(util.as_string(url.replace('_', '=')[5:]))

class PackageInfo:
    def __init__(self, name=None, url=None, fname=None):
        self.name = name
        self.url = url
        self.fname = fname

    def to_name(self):
        if self.name is not None: return self.name
        if self.url is not None: return self.url
        return None

    def to_fname(self):
        if self.fname is None: self.fname = self.get_encoded_name_url()
        return self.fname

    def get_encoded_name_url(self):
        if self.name is None: return encode_url(self.url)
        else: return self.name.replace('/', '__')


def fname_to_pkg(fname):
    if fname.startswith('_url_'): return PackageInfo(name=decode_url(fname), fname=fname)
    else: return PackageInfo(name=fname.replace('__', '/'), fname=fname)

