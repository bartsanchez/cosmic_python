import uuid

import pytest
import requests

import config


@pytest.fixture
def add_stock(postgres_session):
    batches_added = set()
    skus_added = set()

    def _add_stock(lines):
        for ref, sku, qty, eta in lines:
            postgres_session.execute(
                "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
                " VALUES (:ref, :sku, :qty, :eta)",
                dict(ref=ref, sku=sku, qty=qty, eta=eta),
            )
            [[batch_id]] = postgres_session.execute(
                "SELECT id FROM batches WHERE reference=:ref AND sku=:sku",
                dict(ref=ref, sku=sku),
            )
            batches_added.add(batch_id)
            skus_added.add(sku)
        postgres_session.commit()

    yield _add_stock

    for batch_id in batches_added:
        postgres_session.execute(
            "DELETE FROM allocations WHERE batch_id=:batch_id",
            dict(batch_id=batch_id),
        )
        postgres_session.execute(
            "DELETE FROM batches WHERE id=:batch_id", dict(batch_id=batch_id),
        )
    for sku in skus_added:
        postgres_session.execute(
            "DELETE FROM order_lines WHERE sku=:sku", dict(sku=sku),
        )
        postgres_session.commit()


def random_suffix():
    return uuid.uuid4().hex[:6]


def random_sku(name=""):
    return f"sku-{name}-{random_suffix()}"


def random_batchref(name=""):
    return f"batch-{name}-{random_suffix()}"


def random_orderid(name=""):
    return f"order-{name}-{random_suffix()}"


@pytest.mark.usefixtures("restart_api")
def test_api_returns_allocation(add_stock):
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    _ = random_batchref(3)
    add_stock(
        [
            (laterbatch, sku, 100, "2011-01-02"),
            (earlybatch, sku, 100, "2011-01-01"),
            (laterbatch, othersku, 100, None),
        ]
    )
    data = {"order_reference": random_orderid(), "sku": sku, "quantity": 3}
    url = config.get_api_url()

    r = requests.post(f"{url}/allocate", json=data)

    assert r.status_code == 201
    assert r.json()["batchref"] == earlybatch


@pytest.mark.usefixtures("restart_api")
def test_allocations_are_persisted(add_stock):
    sku = random_sku()
    batch1, batch2 = random_batchref(1), random_batchref(2)
    order1, order2 = random_orderid(1), random_orderid(2)
    add_stock(
        [(batch1, sku, 10, "2011-01-01"), (batch2, sku, 10, "2011-01-02")]
    )
    line1 = {"order_reference": order1, "sku": sku, "quantity": 10}
    line2 = {"order_reference": order2, "sku": sku, "quantity": 10}
    url = config.get_api_url()

    r = requests.post(f"{url}/allocate", json=line1)
    assert r.status_code == 201
    assert r.json()["batchref"] == batch1

    r = requests.post(f"{url}/allocate", json=line2)
    assert r.status_code == 201
    assert r.json()["batchref"] == batch2
