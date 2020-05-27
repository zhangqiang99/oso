from pathlib import Path

from polar import Polar
from polar.test_helpers import db, polar, tell, load_file, query, qeval, qvar

import pytest


def test_anything_works():
    p = Polar()
    p.load_str("f(1);")
    results = list(p.query_str("f(x)"))
    assert results[0]["x"] == 1
    results = list(p.query_str("f(y)"))
    assert results[0]["y"] == 1
    del p


def test_helpers(polar, load_file, query, qeval, qvar):
    load_file(Path(__file__).parent / "test_file.polar")  # f(1);
    assert query("f(x)") == [{"x": 1}, {"x": 2}, {"x": 3}]
    assert qvar("f(x)", "x") == [1, 2, 3]


def test_data_conversions(polar, qvar):
    polar.load_str('a(1);b("two");c(true);d([1,"two",true]);')
    assert qvar("a(x)", "x", one=True) == 1
    assert qvar("b(x)", "x", one=True) == "two"
    assert qvar("c(x)", "x", one=True)
    assert qvar("d(x)", "x", one=True) == [1, "two", True]


def test_external(polar, qvar):
    class Bar:
        def y(self):
            return "y"

    class Foo:
        def __init__(self, a="a"):
            self.a = a

        def b(self):
            yield "b"

        def c(self):
            return "c"

        def d(self, x):
            return x

        def bar(self):
            return Bar()

        def e(self):
            return [1, 2, 3]

        def f(self):
            yield [1, 2, 3]
            yield [4, 5, 6]
            yield 7

        def g(self):
            return {"hello": "world"}

        def h(self):
            return True

    def capital_foo():
        return Foo(a="A")

    polar.register_python_class(Foo, from_polar=capital_foo)
    assert qvar("Foo{}.a = x", "x", one=True) == "A"
    assert qvar("Foo{}.a() = x", "x", one=True) == "A"
    assert qvar("Foo{}.b = x", "x", one=True) == "b"
    assert qvar("Foo{}.b() = x", "x", one=True) == "b"
    assert qvar("Foo{}.c = x", "x", one=True) == "c"
    assert qvar("Foo{}.c() = x", "x", one=True) == "c"
    assert qvar("Foo{} = f, f.a() = x", "x", one=True) == "A"
    assert qvar("Foo{}.bar().y() = x", "x", one=True) == "y"
    assert qvar("Foo{}.e = x", "x", one=True) == [1, 2, 3]
    assert qvar("Foo{}.f = x", "x") == [[1, 2, 3], [4, 5, 6], 7]
    assert qvar("Foo{}.g.hello = x", "x", one=True) == "world"
    assert qvar("Foo{}.h = x", "x", one=True) is True


def test_specializers(polar, qvar, qeval, query):
    class A:
        def a(self):
            return "A"

        def x(self):
            return "A"

    class B(A):
        def b(self):
            return "B"

        def x(self):
            return "B"

    class C(B):
        def c(self):
            return "C"

        def x(self):
            return "C"

    class X:
        def x(self):
            return "X"

    polar.register_python_class(A)
    polar.register_python_class(B)
    polar.register_python_class(C)
    polar.register_python_class(X)

    rules = """
    test(A{});
    test(B{});
    
    try(v: B{}, res) := res = 2;
    try(v: C{}, res) := res = 3;
    try(v: A{}, res) := res = 1;
    """
    polar.load_str(rules)

    assert qvar("A{}.a = x", "x", one=True) == "A"
    assert qvar("A{}.x = x", "x", one=True) == "A"
    assert qvar("B{}.a = x", "x", one=True) == "A"
    assert qvar("B{}.b = x", "x", one=True) == "B"
    assert qvar("B{}.x = x", "x", one=True) == "B"
    assert qvar("C{}.a = x", "x", one=True) == "A"
    assert qvar("C{}.b = x", "x", one=True) == "B"
    assert qvar("C{}.c = x", "x", one=True) == "C"
    assert qvar("C{}.x = x", "x", one=True) == "C"
    assert qvar("X{}.x = x", "x", one=True) == "X"

    assert len(query("test(A{})")) == 1
    assert len(query("test(B{})")) == 2

    assert qvar("try(A{}, x)", "x") == [1]
    assert qvar("try(B{}, x)", "x") == [2, 1]
    assert qvar("try(C{}, x)", "x") == [3, 2, 1]
    assert qvar("try(X{}, x)", "x") == []