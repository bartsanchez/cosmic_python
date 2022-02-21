from flask import Flask
from flask import request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
import model
import orm
import repository
import service


orm.start_mappers()
get_session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
app = Flask(__name__)


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    session = get_session()

    batches = repository.SqlAlchemyRepository(session).list()
    line = model.OrderLine(
        order_reference=request.json["order_reference"],
        sku=request.json["sku"],
        quantity=request.json["quantity"],
    )

    if not is_valid_sku(line.sku, batches):
        return {"message": f"Invalid sku {line.sku}"}, 400

    try:
        batchref = service.allocate(line, batches)
    except service.OutOfStock as e:
        return {"message": str(e)}, 400

    session.commit()
    return {"batchref": batchref}, 201
