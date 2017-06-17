# coding: utf-8

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField, BooleanField, TextAreaField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    name = StringField(u'用户名', validators=[DataRequired()])
    passwd = PasswordField(u'密码', validators=[DataRequired()])
class PasswdForm(FlaskForm):
    old_pass = PasswordField(u'旧密码', validators=[DataRequired()])
    new_pass = PasswordField(u'新密码', validators=[DataRequired()])
    rep_pass = PasswordField(u'重复密码', validators=[DataRequired()])
class MysqlDbForm(FlaskForm):
    name = StringField(u'名称', validators=[DataRequired()])
    host = StringField(u'主机', validators=[DataRequired()])
    port = IntegerField(u'端口', validators=[DataRequired()])
    user = StringField(u'用户名', validators=[DataRequired()])
    password = PasswordField(u'密码')
class UserForm(FlaskForm):
    name = StringField(u'用户名', validators=[DataRequired()])
    passwd = PasswordField(u'密码', validators=[DataRequired()])
    role = StringField(u'角色', validators=[DataRequired()])
    email = StringField(u'邮箱', validators=[DataRequired()])
class WorkForm(FlaskForm):
    name = StringField(u'工单名', validators=[DataRequired()])
    db_config = StringField(u'数据库', validators=[DataRequired()])
    backup = BooleanField(u'备份', validators=[DataRequired()])
    audit = StringField(u'审核人', validators=[DataRequired()])
    sql_content = TextAreaField(u'sql内容', validators=[DataRequired()])
class WorkAssignForm(FlaskForm):
    audit = StringField(u'审核人', validators=[DataRequired()])
class ReportForm(FlaskForm):
    mem = StringField(u'内存大小', validators=[DataRequired()])
