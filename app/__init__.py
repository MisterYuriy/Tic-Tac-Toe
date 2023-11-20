from flask import Flask
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

from app.config import Config
from app.database import engine

app = Flask(__name__)
app.config.from_object(Config)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

from app import routes  # noqa: E402
from app.models import Base  # noqa: E402

Base.metadata.create_all(engine)
