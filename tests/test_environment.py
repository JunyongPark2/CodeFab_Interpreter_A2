import pytest

from interpreter.environment import Environment
from interpreter.errors import LangRuntimeError


def test_define_and_get_in_same_environment():
    env = Environment()
    env.define("a", 1.0)
    assert env.get("a") == 1.0


def test_get_falls_back_to_parent_chain():
    parent = Environment()
    parent.define("a", 1.0)
    child = Environment(parent=parent)
    assert child.get("a") == 1.0


def test_get_undefined_raises():
    env = Environment()
    with pytest.raises(LangRuntimeError):
        env.get("nope")


def test_assign_updates_nearest_defining_ancestor():
    parent = Environment()
    parent.define("a", 1.0)
    child = Environment(parent=parent)
    child.assign("a", 2.0)
    assert parent.get("a") == 2.0
    assert "a" not in child.names


def test_assign_undefined_raises():
    env = Environment()
    with pytest.raises(LangRuntimeError):
        env.assign("nope", 1.0)


# ── 실행 전 최적화: 정적 바인딩용 O(1) 접근 ────────────────────────
def test_get_at_zero_reads_own_scope():
    env = Environment()
    env.define("a", 1.0)
    assert env.get_at(0, "a") == 1.0


def test_get_at_distance_climbs_exact_number_of_ancestors():
    grandparent = Environment()
    grandparent.define("a", 1.0)
    parent = Environment(parent=grandparent)
    child = Environment(parent=parent)
    assert child.get_at(2, "a") == 1.0


def test_assign_at_zero_writes_own_scope():
    env = Environment()
    env.define("a", 1.0)
    env.assign_at(0, "a", 9.0)
    assert env.get("a") == 9.0


def test_assign_at_distance_writes_exact_ancestor_not_nearer_shadow():
    # child가 같은 이름 a를 자기 스코프에 새로 갖고 있어도, distance=1로 지정하면
    # child가 아니라 parent의 a를 덮어써야 한다 (정적 바인딩의 핵심 보장).
    parent = Environment()
    parent.define("a", 1.0)
    child = Environment(parent=parent)
    child.define("a", 100.0)

    child.assign_at(1, "a", 5.0)

    assert parent.get("a") == 5.0
    assert child.get_at(0, "a") == 100.0
