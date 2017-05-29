# coding: utf-8
from app import app, db
from flask import render_template, redirect, current_app, g, session, request, flash, make_response, send_file
from flask_login import current_user,login_user, logout_user ,login_required
from app.form import *
from app.models import *
from werkzeug.security import generate_password_hash, check_password_hash
from flask_principal import Identity, AnonymousIdentity, identity_changed, Permission, RoleNeed
from datetime import datetime, date, timedelta
import json, re, os
from app.inception import Inception
config=app.config

inc=Inception()

admin_permission = Permission(RoleNeed('admin'))
dev_permission = Permission(RoleNeed('dev'))
audit_permission = Permission(RoleNeed('audit'))

@app.before_request
def before_request():
    g.user = current_user

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
@app.route('/user/srole/<int:id>')
@admin_permission.require()
def user_srole(id):
    user = User.query.get(id)
    if user.srole == 0:
        user.srole = 1
    else:
        user.srole = 0
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
    if config.get('AUDIT_SROLE_ON_OFF') == 'ON':
        audits = User.query.filter(User.role == 'audit', User.srole == 1)
    else:
        audits = User.query.filter(User.role == 'audit', User.srole == 0)
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
            audit=User.query.filter(User.name == work.audit).first()
            work.srole = audit.srole
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
                work.auto_review = jsonResult
                work.create_time = datetime.now()

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
                work.auto_review = jsonResult
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
@app.route('/dev_chart/<int:days>')
@dev_permission.require()
def dev_chart(days=7):
    dayrange=[]
    today = date.today()
    dayrange.append(str(today))
    for day in range(1,days):
        datetmp = today-timedelta(days=day)
        dayrange.append(str(datetmp))
    dayrange.sort()

    daycounts=[]
    for i in range(len(dayrange)):
        daycount=Work.query.filter(Work.dev == current_user.name, Work.create_time.like(dayrange[i]+'%')).count()
        daycounts.append(daycount)
    sevendayago = today-timedelta(days=days)
    works = Work.query.filter(Work.dev == current_user.name, Work.create_time >= sevendayago).group_by(Work.status)
    workstatus={u'正常结束':0, u'待人工审核':0, u'自动审核失败':0, u'执行中':0, u'执行异常':0, u'开发人中止':0, u'审核人中止':0, u'管理员中止':0}
    for work in works:
        if work.status == 0:
            workstatus[u'正常结束']+=1
        elif work.status == 1:
            workstatus[u'待人工审核']+=1
        elif work.status == 2:
            workstatus[u'自动审核失败']+=1
        elif work.status == 3:
            workstatus[u'执行中']+=1
        elif work.status == 4:
            workstatus[u'执行异常']+=1
        elif work.status == 5:
            workstatus[u'开发人中止']+=1
        elif work.status == 6:
            workstatus[u'审核人中止']+=1
        elif work.status == 7:
            workstatus[u'管理员中止']+=1


    return render_template('dev_chart.html',dayrange=dayrange, daycounts=daycounts, workstatus=workstatus, days=days)




@app.route('/audit_work')
@audit_permission.require()
def audit_work():
    works = Work.query.filter(Work.audit == current_user.name, Work.status != 1)
    return render_template('audit_work.html', works=works)
@app.route('/audit_work_pending')
@audit_permission.require()
def audit_work_pending():
    works = Work.query.filter(Work.audit == current_user.name, Work.status == 1)
    return render_template('audit_work_pending.html', works=works)
@app.route('/audit_work/assign/<int:id>', methods = ['GET', 'POST'])
@audit_permission.require()
def audit_work_assign(id):
    work = Work.query.get(id)
    audits = User.query.filter(User.role == 'audit', User.srole == 0)
    form=WorkAssignForm()
    if form.validate_on_submit():
        work.srole = 0
        work.audit = form.audit.data
        db.session.commit()
        return redirect('audit_work')

    return render_template('audit_work_assign.html', form=form, work=work, audits=audits)
@app.route('/audit_work/execute/<int:id>')
@audit_permission.require()
def audit_work_execute(id):
    work = Work.query.filter(Work.audit == current_user.name, Work.id == id).first()
    work.status = 3
    work.man_review_time = datetime.now()
    db.session.commit()

    (finalStatus, finalList)=inc.executeFinal(work)
    jsonResult = json.dumps(finalList)
    work.execute_result = jsonResult
    work.finish_time = datetime.now()
    work.status = finalStatus
    db.session.commit()
    return redirect('audit_work')
@app.route('/audit_work/exportsql/<int:id>')
@audit_permission.require()
def audit_work_exportsql(id):
    listSqlBak = inc.getRollbackSqlList(id)
    base_dir = os.path.dirname(__file__)
    tmp_dir = base_dir+'/temp'
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    fp = open(tmp_dir + '/backup.sql', 'w')
    for i in range(len(listSqlBak)):
        fp.write(listSqlBak[i]+'\n')
    fp.close()
    response = make_response(send_file(tmp_dir + '/backup.sql'))
    response.headers["Content-Disposition"] = "attachment; filename=ex.sql;"
    return response




@app.route('/work/view/<int:id>')
@login_required
def work_view(id):
    work = Work.query.get(id)
    if work.status == 0:
        review_content=json.loads(work.execute_result)
    else:
        review_content=json.loads(work.auto_review)
    return render_template('work_view.html', work=work, review_content=review_content)

@app.route('/work/stop/<int:id>')
@login_required
def work_stop(id):
    work = Work.query.get(id)
    if current_user.role == 'dev':
        work.status = 5
        work.finish_time = datetime.now()
        db.session.commit()
        return redirect('dev_work')
    elif current_user.role == 'audit':
        work.status = 6
        work.finish_time = datetime.now()
        db.session.commit()
        return redirect('audit_work')
    elif current_user.role == 'admin':
        work.status = 7
        work.finish_time = datetime.now()
        db.session.commit()



