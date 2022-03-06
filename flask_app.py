from flask import Flask
from flask import request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
from domain import model
import orm
import repository
import service


orm.start_mappers()
get_session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    session = get_session()
    repo = repository.SqlAlchemyRepository(session)
    line = model.OrderLine(
        order_reference=request.json["order_reference"],
        sku=request.json["sku"],
        quantity=request.json["quantity"],
    )

    try:
        batchref = service.allocate(line, repo, session)
    except (model.OutOfStock, service.InvalidSku) as e:
        return {"message": str(e)}, 400

    return {"batchref": batchref}, 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():
    session = get_session()
    repo = repository.SqlAlchemyRepository(session)
    order_reference = request.json["order_reference"]
    sku = request.json["sku"]
    try:
        batchref = service.deallocate(order_reference, sku, repo, session)
    except (model.OutOfStock, service.InvalidSku) as e:
        return {"message": str(e)}, 400

    return {"batchref": batchref}, 201
