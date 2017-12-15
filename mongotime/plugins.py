from os import path, listdir
from inspect import isclass


PLUGIN_PATH = path.expanduser('~/.mongotime/plugins')


class Aspect(object):
    def get_value(self, op, aspects):
        raise NotImplementedError

    def get_name(self):
        if hasattr(self, 'name'):
            return getattr(self, 'name')
        return self.__class__.__name__


def load_plugins():
    plugins = {
        'aspects': [],
    }

    if not path.isdir(PLUGIN_PATH):
        return plugins

    module_files = [
        f for f in listdir(PLUGIN_PATH)
        if (f.endswith('.py') and
            not f.startswith('_') and
            path.isfile(path.join(PLUGIN_PATH, f)))
    ]

    # Load by executing the file, gathering results in a dict, and checking
    # those for classes that look like an aspect.
    for module_file in module_files:
        namespace = {}
        execfile(path.join(PLUGIN_PATH, module_file), namespace)

        plugins['aspects'] += [
            thing for thing in namespace.itervalues()
            if (isclass(thing) and
                issubclass(thing, Aspect) and
                thing is not Aspect)
        ]

    return plugins
