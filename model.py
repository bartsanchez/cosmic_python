from datetime import date
from dataclasses import dataclass


class OutOfStock(Exception):
    pass


class ReferenceAndSkuNotFound(Exception):
    pass


@dataclass(unsafe_hash=True)
class OrderLine:
    order_reference: str
    sku: str
    quantity: int


class Batch:
    def __init__(self, reference: str, sku: str, quantity: int, eta: date):
        self.reference = reference
        self.sku = sku
        self.eta = eta
        self._purchased_quantity = quantity
        self._allocations: set[OrderLine] = set()

    def __gt__(self, other):
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def __eq__(self, other):
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __hash__(self):
        return hash(self.reference)

    @property
    def allocated_quantity(self) -> int:
        return sum(allocation.quantity for allocation in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity

    def allocate(self, order_line: OrderLine) -> None:
        if self.can_allocate(order_line):
            self._allocations.add(order_line)

    def deallocate(self, order_line: OrderLine) -> None:
        if order_line in self._allocations:
            self._allocations.remove(order_line)

    def can_allocate(self, order_line: OrderLine) -> bool:
        return (
            self.sku == order_line.sku
            and self.available_quantity >= order_line.quantity
        )

    def can_deallocate(self, order_reference: str, sku: str) -> bool:
        return (order_reference, sku) in (
            (o.order_reference, o.sku) for o in self._allocations
        )


def allocate(line: OrderLine, batches: list[Batch]) -> str:
    try:
        batch = next(b for b in sorted(batches) if b.can_allocate(line))
        batch.allocate(line)
        return batch.reference
    except StopIteration:
        raise OutOfStock(f"Out of stock for sku {line.sku}")


def deallocate(order_reference: str, sku: str, batches: list[Batch]) -> str:
    try:
        batch = next(
            b for b in sorted(batches) if b.can_deallocate(order_reference, sku)
        )
        order_line = next(
            line
            for line in batch._allocations
            if (order_reference, sku) == (line.order_reference, line.sku)
        )
        batch.deallocate(order_line)
        return batch.reference
    except StopIteration:
        raise ReferenceAndSkuNotFound(
            f"Order line not found for such reference {order_reference} and sku {sku}"
        )
