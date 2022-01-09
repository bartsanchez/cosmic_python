from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.orm import mapper

import model

metadata = MetaData()

order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("order_reference", String(255)),
    Column("sku", String(255)),
    Column("quantity", Integer, nullable=False),
)


def start_mappers():
    lines_mapper = mapper(model.OrderLine, order_lines)
