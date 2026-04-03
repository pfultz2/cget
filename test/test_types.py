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


# ── Additional decorator_with_args tests ─────────────────────────────────────

class TestDecoratorWithArgsAdditional:
    def test_with_no_args(self):
        @decorator_with_args
        def noop_decorator(f):
            return f

        @noop_decorator()
        def func():
            return 99

        assert func() == 99

    def test_with_kwargs(self):
        @decorator_with_args
        def multiply(f, factor=1):
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs) * factor
            return wrapper

        @multiply(factor=3)
        def get_five():
            return 5

        assert get_five() == 15

    def test_preserves_function_args(self):
        @decorator_with_args
        def log_decorator(f, prefix=""):
            def wrapper(*args, **kwargs):
                return prefix + str(f(*args, **kwargs))
            return wrapper

        @log_decorator(prefix="result: ")
        def add(a, b):
            return a + b

        assert add(1, 2) == "result: 3"


# ── Additional is_iterable tests ────────────────────────────────────────────

class TestIsIterableAdditional:
    def test_float(self):
        assert is_iterable(3.14) is False

    def test_bool(self):
        assert is_iterable(True) is False

    def test_bytes(self):
        assert is_iterable(b"hello") is True

    def test_custom_iterable(self):
        class MyIter:
            def __iter__(self):
                return iter([])
        assert is_iterable(MyIter()) is True

    def test_range(self):
        assert is_iterable(range(10)) is True


# ── Additional default_checker tests ────────────────────────────────────────

class TestDefaultCheckerAdditional:
    def test_none_type(self):
        result, msg = default_checker(None, type(None))
        assert result is True

    def test_custom_class(self):
        class Foo:
            pass
        result, msg = default_checker(Foo(), Foo)
        assert result is True

    def test_inheritance(self):
        class Base:
            pass
        class Sub(Base):
            pass
        result, _ = default_checker(Sub(), Base)
        assert result is True


# ── Additional callable_checker tests ───────────────────────────────────────

class TestCallableCheckerAdditional:
    def test_lambda(self):
        check = lambda x: x > 0
        result, name = callable_checker(5, check)
        assert result is True
        assert name == "<lambda>"

    def test_method(self):
        class Validator:
            @staticmethod
            def is_even(x):
                return x % 2 == 0
        result, name = callable_checker(4, Validator.is_even)
        assert result is True


# ── Additional get_checker tests ────────────────────────────────────────────

class TestGetCheckerAdditional:
    def test_class_mismatch(self):
        checker = get_checker(int)
        result, msg = checker("hello", int)
        assert result is False

    def test_callable_mismatch(self):
        def is_positive(x):
            return x > 0
        checker = get_checker(is_positive)
        result, _ = checker(-1, is_positive)
        assert result is False

    def test_iterable_no_match(self):
        checker = get_checker([int, float])
        result, _ = checker("hello", [int, float])
        assert result is False

    def test_iterable_second_type_matches(self):
        checker = get_checker([int, str])
        result, _ = checker("hello", [int, str])
        assert result is True


# ── Additional require_type tests ───────────────────────────────────────────

class TestRequireTypeAdditional:
    def test_with_callable_checker(self):
        def is_positive(x):
            return x > 0
        result = require_type(5, is_positive, "func")
        assert result == 5

    def test_with_callable_checker_fail(self):
        def is_positive(x):
            return x > 0
        with pytest.raises(TypeError):
            require_type(-1, is_positive, "func", "x")

    def test_with_iterable_type(self):
        result = require_type("hello", [int, str], "func", "x")
        assert result == "hello"

    def test_with_iterable_type_fail(self):
        with pytest.raises(TypeError):
            require_type([], [int, str], "func", "x")


# ── format_checkers additional ──────────────────────────────────────────────

class TestFormatCheckersAdditional:
    def test_empty_list(self):
        result = format_checkers([])
        assert result == "()"

    def test_single_failure(self):
        result = format_checkers([(False, "type 'int'")])
        assert "int" in result
