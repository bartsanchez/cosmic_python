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


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    session = get_session()

    batches = repository.SqlAlchemyRepository(session).list()
    line = model.OrderLine(
        order_reference=request.json["order_reference"],
        sku=request.json["sku"],
        quantity=request.json["quantity"],
    )

    batchref = service.allocate(line, batches)

    session.commit()
    return {"batchref": batchref}, 201
