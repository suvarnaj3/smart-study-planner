"""
dsa/priority_queue.py
Custom Binary Max Heap Priority Queue Implementation.

This module implements a Max Heap data structure from scratch using a zero-indexed array.
Used by the Greedy Scheduler to dynamically manage and retrieve highest-priority topics.

Time Complexities:
- Insert (push): O(log N)
- Extract Max (pop): O(log N)
- Peek: O(1)
- Size / Is Empty: O(1)
"""

from typing import Any, List, Optional, Tuple, TypeVar, Generic

T = TypeVar("T")


class HeapNode(Generic[T]):
    """
    Internal node wrapping priority score, sequence counter for tie-breaking, and stored item.
    """
    def __init__(self, priority: float, seq: int, item: T):
        self.priority = priority
        self.seq = seq
        self.item = item

    def __gt__(self, other: "HeapNode[T]") -> bool:
        """
        Max-Heap comparison:
        1. Higher priority comes first.
        2. If priority is tied, earlier inserted item (smaller seq) comes first.
        """
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.seq < other.seq

    def __ge__(self, other: "HeapNode[T]") -> bool:
        return self > other or (self.priority == other.priority and self.seq == other.seq)

    def __lt__(self, other: "HeapNode[T]") -> bool:
        return not (self >= other)

    def __le__(self, other: "HeapNode[T]") -> bool:
        return not (self > other)


class MaxHeap(Generic[T]):
    """
    Zero-indexed Binary Max Heap implementation from scratch.
    """

    def __init__(self):
        self._heap: List[HeapNode[T]] = []
        self._counter: int = 0  # Global insertion sequence counter

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def size(self) -> int:
        return len(self._heap)

    @staticmethod
    def _parent(index: int) -> int:
        return (index - 1) // 2

    @staticmethod
    def _left_child(index: int) -> int:
        return 2 * index + 1

    @staticmethod
    def _right_child(index: int) -> int:
        return 2 * index + 2

    def _sift_up(self, index: int) -> None:
        """
        Restores heap property by moving element at index upwards.
        Time Complexity: O(log N)
        """
        while index > 0:
            parent_idx = self._parent(index)
            if self._heap[index] > self._heap[parent_idx]:
                self._heap[index], self._heap[parent_idx] = self._heap[parent_idx], self._heap[index]
                index = parent_idx
            else:
                break

    def _sift_down(self, index: int) -> None:
        """
        Restores heap property by moving element at index downwards.
        Time Complexity: O(log N)
        """
        n = len(self._heap)
        while True:
            largest = index
            left = self._left_child(index)
            right = self._right_child(index)

            if left < n and self._heap[left] > self._heap[largest]:
                largest = left
            if right < n and self._heap[right] > self._heap[largest]:
                largest = right

            if largest != index:
                self._heap[index], self._heap[largest] = self._heap[largest], self._heap[index]
                index = largest
            else:
                break

    def push(self, priority: float, item: T) -> None:
        """
        Inserts a new item with priority into the max heap.
        Time Complexity: O(log N)
        """
        self._counter += 1
        node = HeapNode(priority, self._counter, item)
        self._heap.append(node)
        self._sift_up(len(self._heap) - 1)

    def insert(self, priority: float, item: T) -> None:
        """Alias for push."""
        self.push(priority, item)

    def pop(self) -> Tuple[float, T]:
        """
        Removes and returns (priority_score, item) for the highest priority element.
        Raises IndexError if heap is empty.
        Time Complexity: O(log N)
        """
        if self.is_empty():
            raise IndexError("pop from an empty PriorityQueue / MaxHeap")

        root_node = self._heap[0]
        last_node = self._heap.pop()

        if not self.is_empty():
            self._heap[0] = last_node
            self._sift_down(0)

        return root_node.priority, root_node.item

    def extract_max(self) -> Tuple[float, T]:
        """Alias for pop."""
        return self.pop()

    def extract_max_item(self) -> T:
        """Removes and returns only the item of the highest priority element."""
        _, item = self.pop()
        return item

    def peek(self) -> Tuple[float, T]:
        """
        Returns (priority_score, item) of the highest priority element without removing it.
        Raises IndexError if heap is empty.
        Time Complexity: O(1)
        """
        if self.is_empty():
            raise IndexError("peek from an empty PriorityQueue / MaxHeap")
        return self._heap[0].priority, self._heap[0].item

    def peek_item(self) -> T:
        """Returns only the item of the highest priority element without removing it."""
        _, item = self.peek()
        return item


# Convenient alias
PriorityQueue = MaxHeap
