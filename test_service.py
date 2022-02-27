from datetime import date
from datetime import timedelta
import pytest

from model import Batch
from model import OrderLine
from model import ReferenceAndSkuNotFound
from repository import AbstractRepository
from service import allocate
from service import deallocate
from service import InvalidSku

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=19)


class FakeRepository(AbstractRepository):
    def __init__(self, batches):
        self._batches = set(batches)

    def add(self, batch):
        self._batches.add(batch)

    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)


class FakeSession:
    commited = False

    def commit(self):
        self.commited = True


def test_returns_allocation():
    line = OrderLine("o1", "COMPLICATED-LAMP", 10)
    batch = Batch("b1", "COMPLICATED-LAMP", 100, eta=None)
    repo = FakeRepository([batch])

    result = allocate(line, repo, FakeSession())
    assert result == "b1"


def test_error_for_invalid_sku():
    line = OrderLine("o1", "NONEXISTENTSKU", 10)
    batch = Batch("b1", "AREALSKU", 100, eta=None)
    repo = FakeRepository([batch])

    with pytest.raises(InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        allocate(line, repo, FakeSession())


def test_commits():
    line = OrderLine("o1", "OMINOUS-MIRROR", 10)
    batch = Batch("b1", "OMINOUS-MIRROR", 100, eta=None)
    repo = FakeRepository([batch])
    session = FakeSession()

    allocate(line, repo, session)
    assert session.commited is True


def test_deallocate_decrements_available_quantity():
    batch = Batch("b1", "BLUE-PLINTH", 100, eta=None)
    repo, session = FakeRepository([batch]), FakeSession()

    allocate(OrderLine("o1", "BLUE-PLINTH", 10), repo, session)
    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90

    deallocate("o1", "BLUE-PLINTH", repo, session)
    assert batch.available_quantity == 100


def test_trying_to_deallocate_unallocated_batch():
    batch = Batch("b1", "AREALSKU", 100, eta=None)
    repo = FakeRepository([batch])

    with pytest.raises(InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        deallocate("o1", "NONEXISTENTSKU", repo, FakeSession())


def test_trying_to_deallocate_incorrect_data_from_batch__reference():
    batch = Batch("b1", "BLUE-PLINTH", 100, eta=None)
    repo, session = FakeRepository([batch]), FakeSession()

    allocate(OrderLine("o1", "BLUE-PLINTH", 10), repo, session)
    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90

    msg = "Order line not found for such reference NONEXISTENTREFERENCE and sku BLUE-PLINTH"
    with pytest.raises(ReferenceAndSkuNotFound, match=msg):
        deallocate("NONEXISTENTREFERENCE", "BLUE-PLINTH", repo, session)
    assert batch.available_quantity == 90


def test_trying_to_deallocate_incorrect_data_from_batch__sku():
    batch = Batch("b1", "BLUE-PLINTH", 100, eta=None)
    repo, session = FakeRepository([batch]), FakeSession()

    allocate(OrderLine("o1", "BLUE-PLINTH", 10), repo, session)
    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90

    with pytest.raises(InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        deallocate("o1", "NONEXISTENTSKU", repo, session)
    assert batch.available_quantity == 90
