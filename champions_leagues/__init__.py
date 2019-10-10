from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

app = Flask(__name__)

# configuration
app.config['SECRET_KEY'] = '6015daea0ab098e971d3deca1f79a5628de25f2d'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost:3306/leagues'
app.config['DEBUG'] = True
try:
    app.config.from_envvar('PRODUCTION_CONFIG')
except:
    pass

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from champions_leagues import routes
from champions_leagues.views.leagues import leagues

app.register_blueprint(leagues)
