import cget.util as util
import pony.orm as pony

db = pony.Database()

class PackageName(db.Entity):
    name = pony.Required(str)
    
class Package(db.Entity):
    names = Set(lambda: PackageName)
    parents = Set('Package', reverse='dependencies')
    dependencies = Set('Package', reverse='parents')

class DirectoryManager:
    def __init__(self, prefix):
        self.prefix = os.path.abspath(prefix or 'cget')

    def load_db(self):
        util.mkdir(self.get_private_path())
        db.bind('sqlite', self.get_private_path('db.sqlite'), create_db=True)

    def get_path(self, *paths):
        return os.path.join(self.prefix, *paths)

    def get_private_path(self, *paths):
        return self.get_path('cget', *paths)



