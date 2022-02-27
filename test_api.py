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
            "DELETE FROM batches WHERE id=:batch_id",
            dict(batch_id=batch_id),
        )
    for sku in skus_added:
        postgres_session.execute(
            "DELETE FROM order_lines WHERE sku=:sku",
            dict(sku=sku),
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
def test_happy_path_returns_201_and_allocated_batch(add_stock):
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    otherbatch = random_batchref(3)
    add_stock(
        [
            (laterbatch, sku, 100, "2011-01-02"),
            (earlybatch, sku, 100, "2011-01-01"),
            (otherbatch, othersku, 100, None),
        ]
    )
    data = {"order_reference": random_orderid(), "sku": sku, "quantity": 3}
    url = config.get_api_url()

    r = requests.post(f"{url}/allocate", json=data)

    assert r.status_code == 201
    assert r.json()["batchref"] == earlybatch


@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    unknown_sku, orderid = random_sku(), random_orderid()
    data = {"order_reference": orderid, "sku": unknown_sku, "quantity": 20}
    url = config.get_api_url()

    r = requests.post(f"{url}/allocate", json=data)

    assert r.status_code == 400
    assert r.json()["message"] == f"Invalid sku {unknown_sku}"


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_deallocate(add_stock):
    sku, order1, order2 = random_sku(), random_orderid(), random_orderid()
    batch = random_batchref()
    add_stock([(batch, sku, 100, "2011-01-2")])

    url = config.get_api_url()
    # fully allocate
    r = requests.post(
        f"{url}/allocate",
        json={"order_reference": order1, "sku": sku, "quantity": 100},
    )
    assert r.json()["batchref"] == batch

    # cannot allocate second order
    r = requests.post(
        f"{url}/allocate",
        json={"order_reference": order2, "sku": sku, "quantity": 100},
    )
    assert r.status_code == 400

    # deallocate
    r = requests.post(
        f"{url}/deallocate",
        json={"order_reference": order1, "sku": sku},
    )
    assert r.ok

    # now we can allocate second order
    r = requests.post(
        f"{url}/allocate",
        json={"order_reference": order2, "sku": sku, "quantity": 100},
    )
    assert r.ok
    assert r.json()["batchref"] == batch
