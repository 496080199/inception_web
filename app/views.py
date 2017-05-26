# coding: utf-8
from app import app, db
from flask import render_template, redirect, current_app, session, request, flash
from flask_login import current_user,login_user, logout_user ,login_required
from app.form import *
from app.models import *
from werkzeug.security import generate_password_hash, check_password_hash
from flask_principal import Identity, AnonymousIdentity, identity_changed, Permission, RoleNeed
from datetime import datetime
import json, re
from app.inception import Inception

inc=Inception()

admin_permission = Permission(RoleNeed('admin'))
dev_permission = Permission(RoleNeed('dev'))
audit_permission = Permission(RoleNeed('audit'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():

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
        dbconfig.password = form.password.data
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
            dbconfig.password = form.password.data
        dbconfig.update_time = datetime.now()
        db.session.commit()
        return redirect('mysql_db')

    return render_template('mysql_db_update.html', form=form, dbconfig=dbconfig)
@app.route('/mysql_db/delete/<int:id>')
@admin_permission.require()
def mysql_db_delete(id):
    dbconfig = DbConfig.query.get(id)
    db.session.delete(dbconfig)
    db.session.commit()
    return redirect('mysql_db')

@app.route('/user')
@admin_permission.require()
def user():
    users = User.query.filter(User.role != 'admin')

    return render_template('user.html', users=users)
@app.route('/user/create', methods = ['GET', 'POST'])
@admin_permission.require()
def user_create():
    form = UserForm()
    if form.validate_on_submit():
        user = User()
        user.name = form.name.data
        user.hash_pass = generate_password_hash(form.passwd.data)
        user.role = form.role.data
        user.email = form.email.data
        db.session.add(user)
        db.session.commit()
        return redirect('user')
    return render_template('user_create.html', form=form)
@app.route('/user/update/<int:id>', methods = ['GET', 'POST'])
@admin_permission.require()
def user_update(id):
    user = User.query.get(id)
    form = UserForm()
    if form.validate_on_submit():
        user.hash_pass = generate_password_hash(form.passwd.data)
        user.email = form.email.data
        db.session.commit()
        return redirect('user')
    return render_template('user_update.html', form=form, user=user)
@app.route('/user/delete/<int:id>', methods = ['GET', 'POST'])
@admin_permission.require()
def user_delete(id):
    user = User.query.get(id)
    db.session.delete(user)
    db.session.commit()
    return redirect('user')


@app.route('/dev_work')
@dev_permission.require()
def dev_work():
    works = Work.query.filter(Work.dev == current_user.name)
    return render_template('dev_work.html', works=works)
@app.route('/dev_work/create', methods = ['GET', 'POST'])
@dev_permission.require()
def dev_work_create():
    db_configs = DbConfig.query.all()
    audits = User.query.filter(User.role == 'audit')
    form = WorkForm()
    if form.validate_on_submit():
        sqlContent=form.sql_content.data
        dbConfig=form.db_config.data
        isBackup=form.backup.data
        sqlContent = sqlContent.rstrip()
        if sqlContent[-1] == ";":
            work = Work()
            work.name = form.name.data
            work.db_config = dbConfig
            work.backup = isBackup
            work.dev = current_user.name
            work.audit = form.audit.data
            work.sql_content = sqlContent

            result = inc.sqlautoReview(sqlContent, dbConfig, isBackup)
            if result or len(result) != 0:
                jsonResult = json.dumps(result)
                work.status = 1
                for row in result:
                    if row[2] == 2:
                        work.status = 2
                        break
                    elif re.match(r"\w*comments\w*", row[4]):
                        work.status = 2
                        break
                work.create_time=datetime.now()
                db.session.add(work)
                db.session.commit()
                return redirect('dev_work')
            else:
                flash('inception返回的结果集为空！可能是SQL语句有语法错误!')
        else:
            flash(u'SQL语句结尾没有以;结尾，请重新修改并提交！')

    return render_template('dev_work_create.html', form=form, db_configs=db_configs, audits=audits)
@app.route('/dev_work/update/<int:id>', methods = ['GET', 'POST'])
@dev_permission.require()
def dev_work_update(id):
    work=Work.query.get(id)
    db_configs = DbConfig.query.all()
    audits = User.query.filter(User.role == 'audit')
    form = WorkForm()
    if form.validate_on_submit():
        sqlContent = form.sql_content.data.rstrip()
        if sqlContent[-1] == ";":
            result = inc.sqlautoReview(sqlContent, work.db_config, work.backup)
            if result or len(result) != 0:
                jsonResult = json.dumps(result)
                work.status = 1
                for row in result:
                    if row[2] == 2:
                        work.status = 2
                        break
                    elif re.match(r"\w*comments\w*", row[4]):
                        work.status = 2
                        break
                work.sql_content = sqlContent
                db.session.commit()
                return redirect('dev_work')
            else:
                flash('inception返回的结果集为空！可能是SQL语句有语法错误!')
        else:
            flash(u'SQL语句结尾没有以;结尾，请重新修改并提交！')
    return render_template('dev_work_update.html', form=form, db_configs=db_configs, audits=audits, work=work)
@app.route('/dev_work/delete/<int:id>', methods = ['GET', 'POST'])
@dev_permission.require()
def dev_work_delete(id):
    work = Work.query.get(id)
    db.session.delete(work)
    db.session.commit()
    return redirect('dev_work')
@app.route('/dev_work/stop/<int:id>', methods = ['GET', 'POST'])
@dev_permission.require()
def dev_work_stop(id):
    work = Work.query.get(id)
    if current_user.role == 'dev':
        work.status = 5
    elif current_user.role == 'audit':
        work.status = 6
    else:
        work.status = 7
    work.finish_time = datetime.now()
    db.session.commit()
    return redirect('dev_work')

@app.route('/dev_work/check', methods = ['POST'])
@dev_permission.require()
def dev_work_check():
    data = request.form
    sqlContent=data['sqlContent']
    dbConfig=data['dbConfig']
    finalResult = {'status': 0, 'msg': 'ok', 'data': []}
    if not sqlContent or not dbConfig:
        finalResult['status'] = 1
        finalResult['msg'] = '数据库或SQL内容可能为空'
        return json.dumps(finalResult)
    sqlContent = sqlContent.rstrip()
    if sqlContent[-1] != ";":
        finalResult['status'] = 2
        finalResult['msg'] = 'SQL语句结尾没有以;结尾，请重新修改并提交！'
        return json.dumps(finalResult)
    result = inc.sqlautoReview(sqlContent, dbConfig)
    if result is None or len(result) == 0:
        finalResult['status'] = 3
        finalResult['msg'] = 'inception返回的结果集为空！可能是SQL语句有语法错误'
        return json.dumps(finalResult)
    finalResult['data'] = result
    return json.dumps(finalResult)

