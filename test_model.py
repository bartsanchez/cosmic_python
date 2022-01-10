from datetime import date

from model import Batch
from model import OrderLine


def make_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("batch-001", sku, batch_qty, eta=date.today()),
        OrderLine("order-ref", sku, line_qty)
    )


def test_allocate_order_line_to_a_batch__available_quantity_is_reduced():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 2)
    assert batch.can_allocate(line)


def test_allocate_order_line_to_a_batch__not_enough_available_quantity():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 25)
    assert batch.can_allocate(line) is False


def test_allocate_order_line_to_a_batch__same_amount_as_available_quantity():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 20)
    assert batch.can_allocate(line)


def test_allocate_order_line_to_a_batch__cant_allocate_same_order_line_twice():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 5)
    batch.allocate(line)
    batch.allocate(line)
    assert batch.available_quantity == 15


def test_cannot_allocate_order_line_to_a_batch_with_different_skus():
    batch = Batch("batch-001", "UNCOMFORTABLE-CHAIR", 100, eta=None)
    line = OrderLine("order-ref", "EXPENSIVE-TOASTER", 10)
    assert batch.can_allocate(line) is False


def test_deallocate():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 5)
    batch.allocate(line)
    batch.deallocate(line)
    assert batch.available_quantity == 20


def test_can_only_deallocate_allocated_lines():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 5)
    batch.deallocate(line)
    assert batch.available_quantity == 20
