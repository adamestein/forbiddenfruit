import ctypes
from functools import wraps
from collections import defaultdict

try:
    import __builtin__
except ImportError:
    # Python 3 support
    import builtins as __builtin__

__version__ = '0.1.0'

__all__ = 'curse', 'reverse'


class PyObject(ctypes.Structure):
    pass


Py_ssize_t = \
    hasattr(ctypes.pythonapi, 'Py_InitModule4_64') \
    and ctypes.c_int64 or ctypes.c_int


PyObject._fields_ = [
    ('ob_refcnt', Py_ssize_t),
    ('ob_type', ctypes.POINTER(PyObject)),
]


class SlotsProxy(PyObject):
    _fields_ = [('dict', ctypes.POINTER(PyObject))]


def patchable_builtin(klass):
    name = klass.__name__
    target = getattr(klass, '__dict__', name)

    proxy_dict = SlotsProxy.from_address(id(target))
    namespace = {}

    ctypes.pythonapi.PyDict_SetItem(
        ctypes.py_object(namespace),
        ctypes.py_object(name),
        proxy_dict.dict,
    )

    return namespace[name]


@wraps(__builtin__.dir)
def __filtered_dir__(obj=None):
    name = hasattr(obj, '__name__') and obj.__name__ or obj.__class__.__name__
    return sorted(set(__dir__(obj)).difference(__hidden_elements__[name]))

# Switching to the custom dir impl declared above
__hidden_elements__ = defaultdict(list)
__dir__ = dir
__builtin__.dir = __filtered_dir__


def curse(klass, attr, value, hide_from_dir=False):
    """Curse a built-in `klass` with `attr` set to `value`

    This function monkey-patches the built-in python object `attr` adding a new
    attribute to it. You can add any kind of argument to the `class`.

    It's possible to attach methods as class methods, just do the following:

      >>> def myclassmethod(cls):
      ...     return cls(1.5)
      >>> curse(float, "myclassmethod", classmethod(myclassmethod))
      >>> float.myclassmethod()
      1.5

    Methods will be automatically bound, so don't forget to add a self
    parameter to them, like this:

      >>> def hello(self):
      ...     return self * 2
      >>> curse(str, "hello", hello)
      >>> "yo".hello()
      "yoyo"
    """
    dikt = patchable_builtin(klass)
    dikt[attr] = value
    if hide_from_dir:
        __hidden_elements__[klass.__name__].append(attr)


def reverse(klass, attr):
    """Reverse a curse in a built-in object

    This function removes *new* attributes. It's actually possible to remove
    any kind of attribute from any built-in class, but just DON'T DO IT :)

    Good:

      >>> curse(str, "blah", "bleh")
      >>> assert "blah" in dir(str)
      >>> reverse(str, "blah")
      >>> assert "blah" not in dir(str)

    Bad:

      >>> reverse(str, "strip")
      >>> " blah ".strip()
      Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
      AttributeError: 'str' object has no attribute 'strip'

    """
    dikt = patchable_builtin(klass)
    del dikt[attr]
