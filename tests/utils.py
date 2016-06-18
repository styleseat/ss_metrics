from __future__ import absolute_import

import sys

import pytest

from ss_metrics.utils import get_function_name


def noop():
    pass


class TestGetFunctionName(object):
    def test_function(self):
        assert get_function_name(noop) == 'tests.utils.noop'

    def test_bound_method(self):
        expected = self.method_name('instance_method')
        actual = get_function_name(type(self)().instance_method)
        assert expected == actual

    def test_unbound_method(self):
        self.unbound_method_test('instance_method')

    def test_class_method(self):
        self.unbound_method_test('class_method')

    def test_static_method(self):
        if sys.version_info < (3, 0):
            # Static methods aren't differentiable from module methods in
            # python 2.
            expected = 'tests.utils.static_method'
            actual = get_function_name(type(self).static_method)
            assert expected == actual
        else:
            self.unbound_method_test('static_method')

    def test_module_is_none(self):
        def f():
            pass

        f.__module__ = None
        with pytest.raises(ValueError):
            get_function_name(f)

    def test_non_function_argument(self):
        with pytest.raises(ValueError):
            get_function_name(type(self))

    def unbound_method_test(self, method):
        expected = self.method_name(method)
        actual = get_function_name(getattr(type(self), method))
        assert expected == actual

    def method_name(self, method):
        return '.'.join(('tests.utils.TestGetFunctionName', method))

    def instance_method(self):
        pass

    @classmethod
    def class_method(cls):
        pass

    @staticmethod
    def static_method(cls):
        pass
