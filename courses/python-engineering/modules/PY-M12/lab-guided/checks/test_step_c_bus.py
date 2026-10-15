"""PY-M12 guided lab, step C (EventBus: observers without shared state). Run: python -m pytest checks/test_step_c_bus.py"""
from __future__ import annotations

import gc
import pytest


def usd(lk, cents: int):
    return lk.Money(cents, "USD")


def test_bus_calls_handlers_in_subscription_order(lk):
    bus, seen = lk.EventBus(), []
    bus.subscribe(lambda e: seen.append(("first", e)))
    bus.subscribe(lambda e: seen.append(("second", e)))
    assert bus.publish("x") == () and seen == [("first", "x"), ("second", "x")]


def test_each_bus_has_its_own_subscribers(lk):
    a, b, seen = lk.EventBus(), lk.EventBus(), []
    a.subscribe(seen.append)
    b.publish("only for b")
    assert seen == [] and a.subscriber_count == 1 and b.subscriber_count == 0


def test_unsubscribe_removes_the_handler_and_is_idempotent(lk):
    bus, seen = lk.EventBus(), []
    off = bus.subscribe(seen.append)
    bus.publish(1); off(); off(); bus.publish(2)
    assert seen == [1] and bus.subscriber_count == 0


def test_the_same_function_can_be_subscribed_twice_and_removed_separately(lk):
    bus, seen = lk.EventBus(), []
    off1 = bus.subscribe(seen.append); bus.subscribe(seen.append)
    bus.publish("a"); off1(); bus.publish("b")
    assert seen == ["a", "a", "b"]


def test_a_failing_handler_does_not_stop_the_others_and_its_error_is_returned(lk):
    bus, seen = lk.EventBus(), []

    def boom(event):
        raise RuntimeError("boom")

    bus.subscribe(seen.append); bus.subscribe(boom); bus.subscribe(lambda e: seen.append("after"))
    errors = bus.publish("e")
    assert seen == ["e", "after"] and len(errors) == 1 and isinstance(errors[0], RuntimeError) and str(errors[0]) == "boom"


def test_base_exceptions_are_not_swallowed(lk):
    bus = lk.EventBus()

    def stop(event):
        raise KeyboardInterrupt

    bus.subscribe(stop)
    with pytest.raises(KeyboardInterrupt):
        bus.publish("e")


def test_a_handler_removed_during_publish_is_not_called_in_that_round(lk):
    bus, seen = lk.EventBus(), []
    offs = {}
    offs["second"] = None
    bus.subscribe(lambda e: (seen.append("first"), offs["second"]()))
    offs["second"] = bus.subscribe(lambda e: seen.append("second"))
    bus.publish("e")
    assert seen == ["first"]


def test_a_handler_may_subscribe_another_during_publish_without_breaking_the_loop(lk):
    bus, seen = lk.EventBus(), []
    bus.subscribe(lambda e: bus.subscribe(seen.append))
    assert bus.publish("a") == ()            # must not raise 'dictionary changed size during iteration'
    bus.publish("b")
    assert seen == ["b"]


class Listener:
    def __init__(self): self.seen = []
    def on_event(self, event): self.seen.append(event)


def test_a_bound_method_subscriber_is_held_weakly(lk):
    bus, listener = lk.EventBus(), Listener()
    bus.subscribe(listener.on_event)
    bus.publish(1)
    assert listener.seen == [1] and bus.subscriber_count == 1
    del listener
    gc.collect()
    assert bus.subscriber_count == 0 and bus.publish(2) == (), "the bus must not keep a subscriber alive (weakref.WeakMethod)"


def test_a_function_subscriber_is_held_normally(lk):
    bus, seen = lk.EventBus(), []
    bus.subscribe(lambda e: seen.append(e))
    gc.collect()
    bus.publish("still here")
    assert seen == ["still here"]
