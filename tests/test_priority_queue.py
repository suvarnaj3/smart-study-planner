"""
tests/test_priority_queue.py
Unit tests for custom Max Heap Priority Queue.
"""

import pytest
from dsa.priority_queue import MaxHeap, PriorityQueue, HeapNode


def test_priority_queue_extracts_highest_priority_first():
    """
    Verifies that the Priority Queue strictly selects and pops elements in descending order of priority.
    Catches array index calculations errors ((i-1)//2, 2i+1, 2i+2), sift-up/down bugs, or Min-Heap inversions.
    """
    pq = PriorityQueue[str]()
    items = [(45.0, "Topic D"), (98.5, "Topic A"), (72.0, "Topic B"), (15.0, "Topic E"), (60.0, "Topic C")]

    for score, name in items:
        pq.push(score, name)

    extracted = [pq.pop()[1] for _ in range(len(items))]
    assert extracted == ["Topic A", "Topic B", "Topic C", "Topic D", "Topic E"]


def test_heap_push_and_pop_order():
    pq = PriorityQueue[str]()
    pq.push(10.0, "low priority")
    pq.push(95.0, "highest priority")
    pq.push(50.0, "medium priority")
    pq.push(75.0, "high priority")

    assert len(pq) == 4
    assert not pq.is_empty()

    priority, item = pq.pop()
    assert priority == 95.0
    assert item == "highest priority"

    priority, item = pq.pop()
    assert priority == 75.0
    assert item == "high priority"

    priority, item = pq.pop()
    assert priority == 50.0
    assert item == "medium priority"

    priority, item = pq.pop()
    assert priority == 10.0
    assert item == "low priority"

    assert len(pq) == 0
    assert pq.is_empty()


def test_heap_property_invariant():
    pq = MaxHeap[int]()
    priorities = [45, 12, 89, 32, 99, 100, 23, 67, 4, 90]

    for p in priorities:
        pq.push(float(p), p)

    # Internal array invariant verification
    for i in range(len(pq._heap)):
        left = 2 * i + 1
        right = 2 * i + 2
        if left < len(pq._heap):
            assert pq._heap[i] >= pq._heap[left], f"Heap invariant broken at index {i} vs left child {left}"
        if right < len(pq._heap):
            assert pq._heap[i] >= pq._heap[right], f"Heap invariant broken at index {i} vs right child {right}"


def test_heap_tie_breaking_fifo():
    pq = PriorityQueue[str]()
    # Push 3 items with identical priority score of 50.0
    pq.push(50.0, "First")
    pq.push(50.0, "Second")
    pq.push(50.0, "Third")

    assert pq.pop()[1] == "First"
    assert pq.pop()[1] == "Second"
    assert pq.pop()[1] == "Third"


def test_empty_heap_exceptions():
    pq = PriorityQueue[str]()
    with pytest.raises(IndexError):
        pq.pop()

    with pytest.raises(IndexError):
        pq.peek()


def test_peek_functionality():
    pq = PriorityQueue[str]()
    pq.push(30.0, "Item A")
    pq.push(80.0, "Item B")

    assert pq.peek() == (80.0, "Item B")
    assert len(pq) == 2  # Ensure peek did not remove item
    assert pq.pop() == (80.0, "Item B")
    assert pq.peek() == (30.0, "Item A")
