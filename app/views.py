# coding: utf-8
from app import app, db
from flask import render_template, redirect, current_app, session
from flask_login import current_user,login_user, logout_user ,login_required
from app.form import *
from app.models import *
from werkzeug.security import generate_password_hash, check_password_hash
from flask_principal import Identity, AnonymousIdentity, identity_changed, Permission, RoleNeed
from datetime import datetime

admin_permission = Permission(RoleNeed('admin'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('dashboard')
    form=LoginForm()
    if form.validate_on_submit():
        user=User.query.filter(User.name == form.name.data).first()
        if user is not None and check_password_hash(user.hash_pass, form.passwd.data):
            login_user(user)
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.id))
            return redirect('dashboard')


    return render_template('login.html', form=form)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())
    return redirect('login')
@app.route('/passwd', methods = ['GET', 'POST'])
@login_required
def passwd():
    form = PasswdForm()
    if form.validate_on_submit():
        if form.new_pass.data == form.rep_pass.data:
            if check_password_hash(current_user.hash_pass, form.old_pass.data):
                current_user.hash_pass = generate_password_hash(form.new_pass.data)
                db.session.commit()
                return redirect('dashboard')


    return render_template('passwd.html', form=form)

@app.route('/mysql_db')
@admin_permission.require()
def mysql_db():
    dbconfigs=DbConfig.query.all()

    return render_template('mysql_db.html',dbconfigs=dbconfigs)
@app.route('/mysql_db/create', methods = ['GET', 'POST'])
@admin_permission.require()
def mysql_db_create():
    form = MysqlDbForm()
    if form.validate_on_submit():
        dbconfig = DbConfig()
        dbconfig.name = form.name.data
        dbconfig.host = form.host.data
        dbconfig.port = form.port.data
        dbconfig.user = form.user.data
        dbconfig.password = generate_password_hash(form.password.data)
        db.session.add(dbconfig)
        db.session.commit()
        return redirect('mysql_db')
    return render_template('mysql_db_create.html', form=form)
@app.route('/mysql_db/update/<int:id>', methods = ['GET', 'POST'])
@admin_permission.require()
def mysql_db_update(id):
    dbconfig=DbConfig.query.get(id)
    form = MysqlDbForm()
    if form.validate_on_submit():
        dbconfig.name = form.name.data
        dbconfig.host = form.host.data
        dbconfig.port = form.port.data
        dbconfig.user = form.user.data
        if form.password.data is not None:
            dbconfig.password = generate_password_hash(form.password.data)
        dbconfig.update_time = datetime.now()
        db.session.commit()
        return redirect('mysql_db')
    form.name.data = dbconfig.name
    form.host.data = dbconfig.host
    form.port.data = dbconfig.port
    form.user.data = dbconfig.user

    return render_template('mysql_db_update.html', form=form, id=id)
@app.route('/mysql_db/delete/<int:id>')
@admin_permission.require()
def mysql_db_delete(id):
    dbconfig = DbConfig.query.get(id)
    db.session.delete(dbconfig)
    db.session.commit()
    return redirect('mysql_db')

