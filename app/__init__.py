from flask import Flask
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_principal import Principal, identity_loaded, RoleNeed, UserNeed
from flask_login import LoginManager, current_user
from werkzeug.security import generate_password_hash


app = Flask(__name__)
app.config.from_object('config')

# load the extension
principals = Principal(app)

login_manager = LoginManager(app)

mail = Mail(app)
db = SQLAlchemy(app)


from app.models import *

db.create_all()


#admin=User()
#admin.name='admin'
#admin.email='admin@admin.cn'
#admin.hash_pass=generate_password_hash('admin')
#db.session.add(admin)
#db.session.commit()


@login_manager.user_loader
def load_user(userid):
    return User.query.get(userid)

@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):

    identity.user = current_user


    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))


    if hasattr(current_user, 'role'):
        identity.provides.add(RoleNeed(current_user.role))


# Setup Flask-User


from app.views import *