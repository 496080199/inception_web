# coding: utf-8
from app import app, mail
from flask_mail import Message
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)
def send_email(subject, body, receiver):
    msg = Message(subject, recipients=[receiver])
    msg.html = body
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return u'发送成功'