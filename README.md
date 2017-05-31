# Inception_web
本系统是MySQL自动化管理工具，配合Inception使用，基于archer进行二次开发，进行了一些补充优化。
## 功能说明：
- __SQL自主审核__
- __自动审核+人工审核__
- __主副人工审核__（可配置)
- __回滚sql下载__
- __数据库配置__
- __用户权限配置__
- __工单查询管理__
- __工单邮件通知__
## 配置文件：
config.py
## 安装配置：
要求：python2.7
建议系统环境：CentOS 7/Ubuntun 14+

1.安装MySQL 5.6+数据库，用于存放系统数据和回滚sql。
建立数据库和用户：
create datbase inception_web character set utf8;
grant all privileges on *.* to inception_web@'%' identified by 'inception_web';
flush privileges;

2.安装Inception(参考文档：http://mysql-inception.github.io/inception-document/install/）
inc.cnf使用之前创建的mysql主机帐号密码

3.下载系统源码
git clone https://github.com/496080199/inception_web.git
或使用zip包下载

3.安装python2.7依赖
安装pip工具，具体网上搜索(下载配置加速可参见https://pypi-mirrors.org/）
cd inception_web
pip install -r requirements.txt

4.启动运行
测试：./debug.sh 

生产：
pip install gunicorn
./start.sh

