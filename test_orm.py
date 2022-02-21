from datetime import date

import model


def test_orderline_mapper_can_load_lines(session):
    session.execute(
        "INSERT INTO order_lines (order_reference, sku, quantity) VALUES "
        '("order1", "RED-CHAIR", 12),'
        '("order1", "RED-TABLE", 13),'
        '("order2", "BLUE-LIPSTICK", 14)'
    )
    expected = [
        model.OrderLine("order1", "RED-CHAIR", 12),
        model.OrderLine("order1", "RED-TABLE", 13),
        model.OrderLine("order2", "BLUE-LIPSTICK", 14),
    ]
    assert session.query(model.OrderLine).all() == expected


def test_orderline_mapper_can_save_lines(session):
    new_line = model.OrderLine("order1", "DECORATIVE-WIDGET", 12)
    session.add(new_line)
    session.commit()

    rows = list(
        session.execute('SELECT order_reference, sku, quantity FROM "order_lines"')
    )
    assert rows == [("order1", "DECORATIVE-WIDGET", 12)]


def test_retrieving_batches(session):
    session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta) VALUES "
        '("batch1", "sku1", 100, NULL)'
    )
    session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta) VALUES "
        '("batch2", "sku2", 200, "2001-01-01")'
    )
    expected = [
        model.Batch("batch1", "sku1", 100, eta=None),
        model.Batch("batch2", "sku2", 200, eta=date(2001, 1, 1)),
    ]
    assert session.query(model.Batch).all() == expected


def test_saving_batches(session):
    batch = model.Batch("batch1", "sku1", 100, eta=None)
    session.add(batch)
    session.commit()

    rows = list(
        session.execute(
            'SELECT reference, sku, _purchased_quantity, eta FROM "batches"'
        )
    )
    assert rows == [("batch1", "sku1", 100, None)]


def test_retrieving_allocations(session):
    session.execute(
        "INSERT INTO order_lines (order_reference, sku, quantity) VALUES "
        '("order1", "sku1", 12)'
    )
    [[orderline_id]] = session.execute(
        "SELECT id FROM order_lines WHERE order_reference=:order_reference AND sku=:sku",
        dict(order_reference="order1", sku="sku1"),
    )
    session.execute(
        "INSERT INTO batches (reference, sku, _purchased_quantity, eta) VALUES "
        '("batch1", "sku1", 100, NULL)'
    )
    [[batch_id]] = session.execute(
        "SELECT id FROM batches WHERE reference=:reference AND sku=:sku",
        dict(reference="batch1", sku="sku1"),
    )
    session.execute(
        "INSERT INTO allocations (orderline_id, batch_id) VALUES (:orderline_id, :batch_id)",
        dict(orderline_id=orderline_id, batch_id=batch_id),
    )

    batch = session.query(model.Batch).one_or_none()
    assert batch.reference == "batch1"
    assert batch._allocations == {model.OrderLine("order1", "sku1", 12)}


def test_saving_allocations(session):
    batch = model.Batch("batch1", "sku1", 100, eta=None)
    line = model.OrderLine("order1", "sku1", 12)
    batch.allocate(line)

    session.add(batch)
    session.commit()

    rows = list(session.execute('SELECT orderline_id, batch_id FROM "allocations"'))
    assert rows == [(batch.id, line.id)]
