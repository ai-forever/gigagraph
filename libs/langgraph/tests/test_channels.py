import operator
from typing import Sequence, Union

import pytest

from langgraph.channels.binop import BinaryOperatorAggregate
from langgraph.channels.last_value import LastValue
from langgraph.channels.topic import Topic
from langgraph.errors import EmptyChannelError, InvalidUpdateError

pytestmark = pytest.mark.anyio


def test_last_value() -> None:
    with LastValue(int).from_checkpoint(None, {}) as channel:
        assert channel.ValueType is int
        assert channel.UpdateType is int

        with pytest.raises(EmptyChannelError):
            channel.get()
        with pytest.raises(InvalidUpdateError):
            channel.update([5, 6])

        channel.update([3])
        assert channel.get() == 3
        channel.update([4])
        assert channel.get() == 4
        checkpoint = channel.checkpoint()
    with LastValue(int).from_checkpoint(checkpoint, {}) as channel:
        assert channel.get() == 4


async def test_last_value_async() -> None:
    async with LastValue(int).afrom_checkpoint(None, {}) as channel:
        assert channel.ValueType is int
        assert channel.UpdateType is int

        with pytest.raises(EmptyChannelError):
            channel.get()
        with pytest.raises(InvalidUpdateError):
            channel.update([5, 6])

        channel.update([3])
        assert channel.get() == 3
        channel.update([4])
        assert channel.get() == 4
        checkpoint = channel.checkpoint()
    async with LastValue(int).afrom_checkpoint(checkpoint, {}) as channel:
        assert channel.get() == 4


def test_topic() -> None:
    with Topic(str).from_checkpoint(None, {}) as channel:
        assert channel.ValueType is Sequence[str]
        assert channel.UpdateType is Union[str, list[str]]

        assert channel.update(["a", "b"])
        assert channel.get() == ["a", "b"]
        assert channel.update([["c", "d"], "d"])
        assert channel.get() == ["c", "d", "d"]
        assert channel.update([])
        with pytest.raises(EmptyChannelError):
            channel.get()
        assert not channel.update([]), "channel already empty"
        assert channel.update(["e"])
        assert channel.get() == ["e"]
        checkpoint = channel.checkpoint()
    with Topic(str).from_checkpoint(checkpoint, {}) as channel:
        assert channel.get() == ["e"]
        with Topic(str).from_checkpoint(checkpoint, {}) as channel_copy:
            channel_copy.update(["f"])
            assert channel_copy.get() == ["f"]
            assert channel.get() == ["e"]


async def test_topic_async() -> None:
    async with Topic(str).afrom_checkpoint(None, {}) as channel:
        assert channel.ValueType is Sequence[str]
        assert channel.UpdateType is Union[str, list[str]]

        assert channel.update(["a", "b"])
        assert channel.get() == ["a", "b"]
        assert channel.update(["b", ["c", "d"], "d"])
        assert channel.get() == ["b", "c", "d", "d"]
        assert channel.update([])
        with pytest.raises(EmptyChannelError):
            channel.get()
        assert not channel.update([]), "channel already empty"
        assert channel.update(["e"])
        assert channel.get() == ["e"]
        checkpoint = channel.checkpoint()
    async with Topic(str).afrom_checkpoint(checkpoint, {}) as channel:
        assert channel.get() == ["e"]


def test_topic_accumulate() -> None:
    with Topic(str, accumulate=True).from_checkpoint(None, {}) as channel:
        assert channel.ValueType is Sequence[str]
        assert channel.UpdateType is Union[str, list[str]]

        assert channel.update(["a", "b"])
        assert channel.get() == ["a", "b"]
        assert channel.update(["b", ["c", "d"], "d"])
        assert channel.get() == ["a", "b", "b", "c", "d", "d"]
        assert not channel.update([])
        assert channel.get() == ["a", "b", "b", "c", "d", "d"]
        checkpoint = channel.checkpoint()
    with Topic(str, accumulate=True).from_checkpoint(checkpoint, {}) as channel:
        assert channel.get() == ["a", "b", "b", "c", "d", "d"]
        assert channel.update(["e"])
        assert channel.get() == ["a", "b", "b", "c", "d", "d", "e"]


async def test_topic_accumulate_async() -> None:
    async with Topic(str, accumulate=True).afrom_checkpoint(None, {}) as channel:
        assert channel.ValueType is Sequence[str]
        assert channel.UpdateType is Union[str, list[str]]

        assert channel.update(["a", "b"])
        assert channel.get() == ["a", "b"]
        assert channel.update(["b", ["c", "d"], "d"])
        assert channel.get() == ["a", "b", "b", "c", "d", "d"]
        assert not channel.update([])
        assert channel.get() == ["a", "b", "b", "c", "d", "d"]
        checkpoint = channel.checkpoint()
    async with Topic(str, accumulate=True).afrom_checkpoint(checkpoint, {}) as channel:
        assert channel.get() == ["a", "b", "b", "c", "d", "d"]
        assert channel.update(["e"])
        assert channel.get() == ["a", "b", "b", "c", "d", "d", "e"]


def test_binop() -> None:
    with BinaryOperatorAggregate(int, operator.add).from_checkpoint(
        None, {}
    ) as channel:
        assert channel.ValueType is int
        assert channel.UpdateType is int

        assert channel.get() == 0

        channel.update([1, 2, 3])
        assert channel.get() == 6
        channel.update([4])
        assert channel.get() == 10
        checkpoint = channel.checkpoint()
    with BinaryOperatorAggregate(int, operator.add).from_checkpoint(
        checkpoint, {}
    ) as channel:
        assert channel.get() == 10


async def test_binop_async() -> None:
    async with BinaryOperatorAggregate(int, operator.add).afrom_checkpoint(
        None, {}
    ) as channel:
        assert channel.ValueType is int
        assert channel.UpdateType is int

        assert channel.get() == 0

        channel.update([1, 2, 3])
        assert channel.get() == 6
        channel.update([4])
        assert channel.get() == 10
        checkpoint = channel.checkpoint()
    async with BinaryOperatorAggregate(int, operator.add).afrom_checkpoint(
        checkpoint, {}
    ) as channel:
        assert channel.get() == 10
