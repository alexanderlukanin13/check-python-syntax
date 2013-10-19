#!/usr/bin/env python
"""Check if code can be compiled in particular version of Python (e.g. 2.6 or 3.3)"""

__version__ = "0.0.1"

import json
import os
import subprocess
import sys
import tempfile
import traceback


def format_exception(ex):
    return ''.join(traceback.format_exception(*sys.exc_info()))


# Some `six`-like helpers
if sys.version_info[0] == 2:
    def itervalues(d):
        return d.itervalues()
else:
    def itervalues(d):
        return d.values()


def _check_all_files(files_or_directories):
    """Check given files or directories recursively.

    Return dictionary {file_name: (is_valid, message)} for all individual files.
    """
    result = {}
    # Collect all files from directories recursively
    all_files = []
    for file_or_directory in files_or_directories:
        if os.path.isdir(file_or_directory):
            file_names = _find_all_files(file_or_directory)
            # Filter out non-python files
            file_names = [x for x in file_names if os.path.splitext(x)[1] == '.py']
        elif os.path.isfile(file_or_directory):
            file_names = [os.path.abspath(file_or_directory)]
        else:
            result[file_or_directory] = [False, 'Target not found']
            continue
        all_files.extend(file_names)
    # Make sure that all files are unique
    all_files = sorted(set(all_files))
    # Try to compile all files in current interpreter and record results
    import py_compile
    temp_file_name = os.path.join(tempfile.gettempdir(), os.path.splitext(os.path.split(__file__)[1])[0] + '.tmp')
    for file_name in all_files:
        try:
            py_compile.compile(file_name, cfile=temp_file_name, doraise=True)
            result[file_name] = [True, 'OK']
        except py_compile.PyCompileError as ex:
            result[file_name] = [False, ex.msg]
    return result


def _find_all_files(target_dir):
    """Find all files in directory and return list of absolute paths."""
    result = []
    for current_dir, dir_names, file_names in os.walk(target_dir):
        result.extend(os.path.join(current_dir, x) for x in file_names)
    return result


def _normalize_versions_list(python_version):
    """Return versions list in normalized form

    python_version: target python version(s)
        Allowed formats: '2.6' or (2,6) or [(2,6),(2,7)] or ['2.6','2.7'] or None

    Returns:
        List of tuples, e.g. [(2,6),(2,7)]

    Raises:
        TypeError
    """
    # Convert comma-separated string to list
    # '2.6,2.7' -> ['2.6', '2.7']
    if isinstance(python_version, str) and ',' in python_version:
        python_version = [x.strip() for x in python_version.split(',') if x.strip()]
    # Convert single string or tuple or list of int to list
    # '2.6' -> [(2.6)]
    # (2,6) -> [(2,6)]
    # [2,6] -> [[2,6]]
    if isinstance(python_version, str):
        python_version = [tuple(int(x) for x in python_version.split('.'))]
    elif isinstance(python_version, (tuple, list)) and all(isinstance(x, int) for x in python_version):
        python_version = [python_version]

    # Convert all version items to tuples
    def convert_item(item):
        if isinstance(item, str):
            try:
                result = tuple(int(x) for x in item.split('.'))
            except ValueError:
                raise TypeError()
        elif isinstance(item, tuple):
            result = item
        elif isinstance(item, list):
            result = tuple(item)
        else:
            raise TypeError()
        if (not isinstance(result, tuple) or
            not 1 <= len(result) <= 2 or
            not all(isinstance(x,int) for x in result) or
            result[0] not in (2,3)):
            raise TypeError()
        return result
    return [convert_item(x) for x in python_version]


def find_python_executable(python_versions):
    """Find python executable name for given python versions
    Args:
        python_versions: List of 1- or 2-tuples, e.g. [(2,6), (2,7)]

    Returns:
        First found Python version and executable name, e.g. ((2,7), 'python2.7')
        None if no Python interpreter is found.
    """
    python_versions = _normalize_versions_list(python_versions)
    for version in python_versions:
        possible_names = ['python' + '.'.join(str(x) for x in version), 'python' + ''.join(str(x) for x in version)]
        if version == (2,):
            possible_names.append('python')
        for python_name in possible_names:
            try:
                process = subprocess.Popen([python_name, '--version'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                process.wait()
                process.stdout.close()
                return (version, python_name)
            except OSError:
                pass
    return (None, None)


def check_python_syntax(files_or_directories, python_version=None, _use_this_python=False):
    """Try to compile target files in the given version of Python.

    Args:
        files_or_directories: list of files or directories to check recursively

    Kwargs:
        python_version: target python version(s)
            Allowed formats: '2.6' or (2,6) or [(2,6),(2,7)] or ['2.6','2.7'] or None
            Actually supported versions are 2.6, 2.7 and 3.2+
            If None, current interpreter is used.
            If multiple versions are specified, first present version is used.
        _use_this_python:
            Return error if current python version differs from python_version
            You should not use it.

    Returns:
        {file_path: [is_valid, message]}

    Raises:
        None
    """
    try:
        # Find existing python version and executable
        if python_version is not None:
            found_python_version, python_executable = find_python_executable(python_version)
            if found_python_version is None:
                return {'<exception>': [False, 'No Python executable found for %r' % python_version]}
            this_python_version = sys.version_info[:min(2, len(found_python_version))]
        else:
            this_python_version = sys.version_info[:2]
        # If this python version is not right, execute required python interpreter in subprocess
        if python_version is not None and found_python_version != this_python_version:
            # Safeguard against infinite recursion
            if _use_this_python:
                return {'<exception>': [False, 'We are in %s instead of %s' % (this_python_version, found_python_version)]}
            # Ugly workaround for "RuntimeError: Bad magic number in .pyc file" error
            # (without it, confusing behavior occurs: first run of "python tests.py" is OK and second run fails
            py_file = os.path.splitext(os.path.abspath(__file__))[0] + '.py'
            pyc_file = os.path.splitext(os.path.abspath(__file__))[0] + '.pyc'
            if os.path.isfile(pyc_file):
                os.remove(pyc_file)
            # Run under specified interpreter
            try:
                process = subprocess.Popen([python_executable, '-B', py_file] + list(files_or_directories),
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                process.wait()
                output = process.stdout.read().decode()
                process.stdout.close()
            except OSError as ex:
                return {'<exception>': [False, 'Failed to execute %s: %s' % (python_executable, ex)]}
            try:
                return json.loads(output)
            except ValueError:
                return {'<exception>': [False, 'Failed to load JSON: ' + repr(output)]}
        else:
            return _check_all_files(files_or_directories)
    except Exception as ex:
        return {'<exception>': [False, format_exception(ex)]}


if __name__ == '__main__':
    try:
        import argparse
    except ImportError:
        json.dump({'<exception>': [False, 'Please install argparse for python%s.%s'%sys.version_info[:2]]}, sys.stdout)
        print('')
        sys.exit(1)
    arguments_parser = argparse.ArgumentParser(description='Perform basic validation (by compilation) of version-specific Python syntax')
    arguments_parser.add_argument('files_or_dirs', nargs='+', help='Python files or directories')
    arguments_parser.add_argument('-v', '--version', nargs='?', help='Python version to use (must be installed)')
    arguments_parser.add_argument('-p', '--pretty', action='store_true', help='output pretty JSON')
    arguments_parser.add_argument('--use-this-python', action='store_true', dest='use_this_python', help=argparse.SUPPRESS)

    arguments = arguments_parser.parse_args(sys.argv[1:])

    result = check_python_syntax(arguments.files_or_dirs, python_version=arguments.version, _use_this_python=arguments.use_this_python)
    # If executed by user, prettify output
    formatting_kwargs = {}
    if arguments.pretty:
        formatting_kwargs = {'sort_keys': True, 'indent': 4, 'separators': (',', ': ')}
    json.dump(result, sys.stdout, **formatting_kwargs)
    print('')

    # Return 1 if there is at least one error, 0 if all is OK
    sys.exit(int(any(not x[0] for x in itervalues(result))))