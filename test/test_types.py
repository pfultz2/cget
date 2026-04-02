import os
import pytest

from cget.types import (
    decorator_with_args,
    identity_decorator,
    is_iterable,
    default_checker,
    callable_checker,
    any_checkers,
    format_checkers,
    get_checker,
    require_type,
    params,
    returns,
)


# ── decorator_with_args ──────────────────────────────────────────────────────

class TestDecoratorWithArgs:
    def test_basic_usage(self):
        @decorator_with_args
        def add_prefix(f, prefix=""):
            def wrapper(*args, **kwargs):
                return prefix + f(*args, **kwargs)
            return wrapper

        @add_prefix(prefix="hello ")
        def greet():
            return "world"

        assert greet() == "hello world"


# ── identity_decorator ───────────────────────────────────────────────────────

class TestIdentityDecorator:
    def test_returns_same_function(self):
        def f():
            return 42
        assert identity_decorator(f) is f

    def test_preserves_behavior(self):
        def f(x):
            return x * 2
        decorated = identity_decorator(f)
        assert decorated(5) == 10


# ── is_iterable ──────────────────────────────────────────────────────────────

class TestIsIterable:
    def test_list(self):
        assert is_iterable([1, 2]) is True

    def test_tuple(self):
        assert is_iterable((1,)) is True

    def test_string(self):
        assert is_iterable("abc") is True

    def test_dict(self):
        assert is_iterable({}) is True

    def test_set(self):
        assert is_iterable(set()) is True

    def test_int(self):
        assert is_iterable(42) is False

    def test_none(self):
        assert is_iterable(None) is False

    def test_generator(self):
        assert is_iterable(x for x in []) is True


# ── default_checker ──────────────────────────────────────────────────────────

class TestDefaultChecker:
    def test_match(self):
        result, msg = default_checker(42, int)
        assert result is True
        assert "int" in msg

    def test_no_match(self):
        result, msg = default_checker("hello", int)
        assert result is False
        assert "int" in msg

    def test_subclass(self):
        result, _ = default_checker(True, int)
        assert result is True  # bool is subclass of int


# ── callable_checker ─────────────────────────────────────────────────────────

class TestCallableChecker:
    def test_passes(self):
        def is_positive(x):
            return x > 0
        result, name = callable_checker(5, is_positive)
        assert result is True
        assert name == "is_positive"

    def test_fails(self):
        def is_positive(x):
            return x > 0
        result, name = callable_checker(-1, is_positive)
        assert result is False


# ── any_checkers ─────────────────────────────────────────────────────────────

class TestAnyCheckers:
    def test_one_true(self):
        assert any_checkers([(True, "a"), (False, "b")]) is True

    def test_all_false(self):
        assert any_checkers([(False, "a"), (False, "b")]) is False

    def test_all_true(self):
        assert any_checkers([(True, "a"), (True, "b")]) is True

    def test_empty(self):
        assert any_checkers([]) is False


# ── format_checkers ──────────────────────────────────────────────────────────

class TestFormatCheckers:
    def test_formats_failed(self):
        result = format_checkers([(False, "type 'int'"), (True, "type 'str'")])
        assert "int" in result
        assert "str" not in result

    def test_all_pass(self):
        result = format_checkers([(True, "type 'int'")])
        assert result == "()"

    def test_all_fail(self):
        result = format_checkers([(False, "a"), (False, "b")])
        assert "a" in result
        assert "b" in result


# ── get_checker ──────────────────────────────────────────────────────────────

class TestGetChecker:
    def test_class_type(self):
        checker = get_checker(int)
        result, _ = checker(42, int)
        assert result is True

    def test_callable_type(self):
        def is_positive(x):
            return x > 0
        checker = get_checker(is_positive)
        result, _ = checker(5, is_positive)
        assert result is True

    def test_iterable_type(self):
        checker = get_checker([int, str])
        result, _ = checker(42, [int, str])
        assert result is True


# ── require_type ─────────────────────────────────────────────────────────────

class TestRequireType:
    def test_valid_type(self):
        result = require_type(42, int, "test_func", "x")
        assert result == 42

    def test_invalid_type(self):
        with pytest.raises(TypeError) as exc_info:
            require_type("hello", int, "test_func", "x")
        assert "Parameter 'x'" in str(exc_info.value)
        assert "test_func" in str(exc_info.value)

    def test_return_check(self):
        with pytest.raises(TypeError) as exc_info:
            require_type("hello", int, "test_func")
        assert "Return" in str(exc_info.value)


# ── params / returns decorators ──────────────────────────────────────────────

class TestParamsReturns:
    def test_params_in_non_debug(self):
        """When DEBUG is not set, params should be a no-op."""
        if not os.environ.get('DEBUG'):
            @params(x=int)
            def f(x):
                return x
            # Should work even with wrong type since DEBUG is off
            assert f("string") == "string"

    def test_returns_in_non_debug(self):
        """When DEBUG is not set, returns should be a no-op."""
        if not os.environ.get('DEBUG'):
            @returns(int)
            def f():
                return "string"
            assert f() == "string"

    def test_decorated_function_works(self):
        @params(x=int)
        def double(x):
            return x * 2
        assert double(5) == 10

    def test_returns_decorated_function_works(self):
        @returns(int)
        def get_value():
            return 42
        assert get_value() == 42
