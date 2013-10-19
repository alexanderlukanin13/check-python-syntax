
===================
Check Python syntax
===================

A simple way to check if particular script or package will compile (not crash with ``SyntaxError``) on particular version of Python.

It can be used at early stage of Python 3 porting, to enforce usage of new-style ``print``, ``except``, ``raise`` and so on,
and at the same time retain Python 2.6 compatibility.

Installation
------------

::

    pip install https://github.com/alexanderlukanin13/check_python_syntax/archive/master.zip

All necessary python versions should also be installed.

Usage from code
---------------

::

    >>> from check_python_syntax import check_python_syntax
    >>> check_python_syntax(['/tmp/code'], python_version='3.4')
    {u'/tmp/code/x.py': [False, u'  File "/tmp/code/x.py", line 2\n    raise Exception, \'a\'\n                   ^\nSyntaxError: invalid syntax\n'], u'/tmp/code/s.py': [True, u'OK'], u'/tmp/code/z.py': [True, u'OK']}

You can specify multiple targets:

::

    >>> check_python_syntax(['/tmp/code/x.py', '/tmp/code/z.py'], python_version='2.6')
    {u'/tmp/code/x.py': [True, u'OK'], u'/tmp/code/z.py': [True, u'OK']}


And multiple versions (first existing version will be used):

::

    >>> check_python_syntax(['/tmp/code/s.py'], python_version=('3.9','3'))
    {u'/tmp/code/s.py': [True, u'OK']}
    >>> check_python_syntax(['/tmp/code/s.py'], python_version='3.9')
    {'<exception>': [False, "No Python executable found for '3.9'"]}

Usage from command line
-----------------------

::

    $ python check_python_syntax.py -v 2.7 -p /tmp/code
    {
        "/tmp/code/s.py": [
            true,
            "OK"
        ],
        "/tmp/code/x.py": [
            true,
            "OK"
        ],
        "/tmp/code/z.py": [
            true,
            "OK"
        ]
    }
    $ echo $?
    0
    $ python check_python_syntax.py -v 3.4 -p /tmp/code
    {
        "/tmp/code/s.py": [
            true,
            "OK"
        ],
        "/tmp/code/x.py": [
            false,
            "  File \"/tmp/code/x.py\", line 2\n    raise Exception, 'a'\n                   ^\nSyntaxError: invalid syntax\n"
        ],
        "/tmp/code/z.py": [
            true,
            "OK"
        ]
    }
    $ echo $?
    1

Tips
----------------

Compiled ``\*.pyc`` files are written to system temp directory (e.g. to ``/tmp``).
To achieve better performance, it's highly recommended to use memory file system (tmpfs).

Example ``/etc/fstab`` entry:::

    tmpfs                /tmp                 tmpfs      size=256m             0 0

