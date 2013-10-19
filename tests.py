#!/usr/bin/env python
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import check_python_syntax


class NormalizeVersionsTest(unittest.TestCase):
    def test(self):
        INPUT_OUTPUT = [
            # Single string
            ('2', [(2,)]),
            ('2.6', [(2,6)]),
            # Comma-separated string
            ('2.6,2.7', [(2,6), (2,7)]),
            # Tuple of strings
            (('2.6','2.7'),[(2,6),(2,7)]),
            # List of strings
            (['2.6','2.7'],[(2,6),(2,7)]),
            # List of tuples
            ([(2,6),(2,7)],[(2,6),(2,7)]),
            # List of lists
            ([[2,6],[2,7]],[(2,6),(2,7)]),
        ]
        for input, output in INPUT_OUTPUT:
            self.assertEqual(output, check_python_syntax._normalize_versions_list(input))
        # Run with bad argument
        self.assertRaises(TypeError, check_python_syntax._normalize_versions_list, 2)
        self.assertRaises(TypeError, check_python_syntax._normalize_versions_list, ('2','6'))
        self.assertRaises(TypeError, check_python_syntax._normalize_versions_list, ['wrong'])
        self.assertRaises(TypeError, check_python_syntax._normalize_versions_list, [object()])


class SubprocessMock(object):

    PIPE = subprocess.PIPE
    STDOUT = subprocess.STDOUT

    def __init__(self):
        self.pythons = []

    def Popen(self, arguments, stdout=None, stderr=None):
        class DummyFile(object):
            def close(self):
                pass
        class process_mock(object):
            def __init__(self):
                self.stdout = DummyFile()
            def wait(self):
                pass
        if arguments[0] not in self.pythons:
            raise OSError()
        return process_mock()


class FindPythonExecutableTest(unittest.TestCase):
    def setUp(self):
        check_python_syntax.subprocess = self.subprocess_mock = SubprocessMock()

    def tearDown(self):
        check_python_syntax.subprocess = subprocess

    def test(self):
        # 2
        self.subprocess_mock.pythons = ['python']
        self.assertEqual(((2,), 'python'), check_python_syntax.find_python_executable([(2,)]))
        # 2.6
        self.subprocess_mock.pythons = ['python2.6']
        self.assertEqual(((2,6), 'python2.6'), check_python_syntax.find_python_executable([(2,6), (2,7)]))
        self.subprocess_mock.pythons = ['python26']
        self.assertEqual(((2,6), 'python26'), check_python_syntax.find_python_executable([(2,6), (2,7)]))
        self.subprocess_mock.pythons = ['python']
        self.assertEqual((None, None), check_python_syntax.find_python_executable([(2,6), (2,7)]))
        # 3
        self.subprocess_mock.pythons = ['python2.6', 'python3', 'python3.2']
        self.assertEqual(((3,), 'python3'), check_python_syntax.find_python_executable([(3,)]))
        self.subprocess_mock.pythons = ['python26', 'python3', 'python32']
        self.assertEqual(((3,), 'python3'), check_python_syntax.find_python_executable([(3,)]))
        self.subprocess_mock.pythons = ['python', 'python3']
        self.assertEqual(((3,), 'python3'), check_python_syntax.find_python_executable([(3,)]))
        self.subprocess_mock.pythons = ['python']
        self.assertEqual((None, None), check_python_syntax.find_python_executable([(3,)]))
        # Only second one is present
        self.subprocess_mock.pythons = ['python3', 'python3.3']
        self.assertEqual(((3,3), 'python3.3'), check_python_syntax.find_python_executable([(3,4), (3,3)]))


class UnexpectedErrorTest(unittest.TestCase):
    def setUp(self):
        def dummy_exception(dummy):
            raise Exception('Unexpected error')
        self._check_all_files = check_python_syntax._check_all_files
        check_python_syntax._check_all_files = dummy_exception

    def tearDown(self):
        check_python_syntax._check_all_files = self._check_all_files

    def test(self):
        result = check_python_syntax.check_python_syntax([os.path.join(tempfile.gettempdir(), 'no_such_file.py')])
        self.assertEqual(1, len(result))
        self.assertFalse(result['<exception>'][0])
        self.assertTrue('Exception: Unexpected error' in result['<exception>'][1])


class MiscErrorsTest(unittest.TestCase):
    def test_python_not_found(self):
        result = check_python_syntax.check_python_syntax([os.path.join(tempfile.gettempdir(), 'no_such_file.py')], python_version='2.100')
        self.assertEqual({'<exception>': [False, "No Python executable found for '2.100'"]}, result)

    def test_invalid_recursive_call(self):
        if sys.version_info[0] == 2:
            python_version = (3,)
        else:
            python_version = (2,)
        result = check_python_syntax.check_python_syntax([os.path.join(tempfile.gettempdir(), 'no_such_file.py')], python_version=python_version, _use_this_python=True)
        if sys.version_info[0] == 2:
            self.assertEqual({'<exception>': [False, "We are in (2,) instead of (3,)"]}, result)
        else:
            self.assertEqual({'<exception>': [False, "We are in (3,) instead of (2,)"]}, result)


class SubprocessFailureTest(unittest.TestCase):
    def setUp(self):
        # First Popen() will succeed, second will raise OSError
        class CustomSubprocessMock(SubprocessMock):
            def Popen(self, arguments, stdout=None, stderr=None):
                if '--version' in arguments:
                    return super(CustomSubprocessMock, self).Popen(arguments, stdout=stdout, stderr=stderr)
                else:
                    raise OSError('Fake error')
        check_python_syntax.subprocess = self.subprocess_mock = CustomSubprocessMock()

    def tearDown(self):
        check_python_syntax.subprocess = subprocess

    def test(self):
        self.subprocess_mock.pythons = ['python2.100']
        result = check_python_syntax.check_python_syntax([os.path.join(tempfile.gettempdir(), 'no_such_file.py')], python_version=(2,100))
        self.assertEqual({'<exception>': [False, 'Failed to execute python2.100: Fake error']}, result)


class InterpreterTest(unittest.TestCase):
    """Base class for particular interpreter test cases. Allows testing of multiple files.

    To create test case, declare subclass with following class variables:
    existing_files = {file_name: content, ...}
    target_files = [file_name, ...] or None
    expected_result = {[is_valid, message], ...}
    python_version = (X,Y)
    """
    existing_files = {}
    target_files = None
    expected_result = {}
    python_version = None

    def setUp(self):
        self.maxDiff = 2000
        # Create files and directories in temp directory
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'check-python-syntax')
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.mkdir(self.temp_dir)
        for relative_path, content in self.existing_files.items():
            full_path = os.path.join(self.temp_dir, relative_path)
            if not os.path.isdir(os.path.dirname(full_path)):
                os.makedirs(os.path.dirname(full_path))
            with open(full_path, 'w') as file:
                file.write(content)

    def test(self):
        expected_result = dict((os.path.normpath(os.path.join(self.temp_dir, x)), y) for x, y in self.expected_result.items())
        if self.target_files:
            target_files = [os.path.join(self.temp_dir, x) for x in self.target_files]
        else:
            target_files = [self.temp_dir]
        result = check_python_syntax.check_python_syntax(target_files, python_version=self.python_version)
        for file_name, value in result.items():
            value[1] = value[1].replace(self.temp_dir.rstrip(os.path.sep), '.')
            if value != expected_result.get(file_name):
                print(file_name)
                print(repr(value[1]))
        self.assertEqual(expected_result, result)

    def tearDown(self):
        # Delete all temporary files
        shutil.rmtree(self.temp_dir)


class DirectoryTest(InterpreterTest):
    """Test processing of directories, individual files and non-existing files"""

    existing_files = {
        'subdir/good.py': "print('Hello world!')",
        'subdir/bad.py': "print('No trailing quote)",
        'subdir/readme.txt': "This file should be ignored",
        'ignored.py': "print('This file is ignored')",
        'individual.py': "print('This file is specified as an individual target')",
    }
    target_files = [
        'subdir',
        'no_such_file.py',
        'individual.py',
    ]
    expected_result = {
        './subdir/good.py': [True, 'OK'],
        './subdir/bad.py': [False, '  File "./subdir/bad.py", line 1\n    print(\'No trailing quote)\n                            ^\nSyntaxError: EOL while scanning string literal\n'],
        './no_such_file.py': [False, 'Target not found'],
        './individual.py': [True, 'OK'],
    }
    python_version = (3,)

    def test(self):
        # Call superclass method explicitly for better stack trace
        super(DirectoryTest, self).test()


# Standard set of test files
STANDARD_SET = {
    # All-good file
    'good.py': 'def f(x):\n  return x*2',
    # Set comprehension: version >= 2.7
    'set_comprehension.py': 'def f(x):\n  return {z*x for z in (1,2,3)}',
    # print statement: version < 3
    'print2.py': 'def f(x):\n    print x',
}



class Python26(InterpreterTest):
    existing_files = STANDARD_SET
    expected_result = {
        'good.py': [True, 'OK'],
        'set_comprehension.py': [False, "SyntaxError: ('invalid syntax', ('./set_comprehension.py', 2, 17, '  return {z*x for z in (1,2,3)}\\n'))\n"],
        'print2.py': [True, 'OK'],
    }
    python_version = (2,6)

    def test(self):
        # Call superclass method explicitly for better stack trace
        super(Python26, self).test()


class Python27(InterpreterTest):
    existing_files = STANDARD_SET
    expected_result = {
        'good.py': [True, 'OK'],
        'set_comprehension.py': [True, 'OK'],
        'print2.py': [True, 'OK']
    }
    python_version = (2,7)

    def test(self):
        # Call superclass method explicitly for better stack trace
        super(Python27, self).test()


class Python3(InterpreterTest):
    existing_files = STANDARD_SET
    expected_result = {
        'good.py': [True, 'OK'],
        'set_comprehension.py': [True, 'OK'],
        'print2.py': [False, '  File "./print2.py", line 2\n    print x\n          ^\nSyntaxError: invalid syntax\n'],
    }
    python_version = (3,)

    def test(self):
        # Call superclass method explicitly for better stack trace
        super(Python3, self).test()


class Python33(InterpreterTest):
    existing_files = {
        'yield_from.py': 'def x():\n    yield from [1,2,3]',
    }
    expected_result = {
        'yield_from.py': [True, 'OK'],
    }
    python_version = [(3,3), (3,4), (3,)]

    def test(self):
        # Call superclass method explicitly for better stack trace
        super(Python33, self).test()


if __name__ == '__main__':
    unittest.main()
