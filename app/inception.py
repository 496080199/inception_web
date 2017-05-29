#-*-coding: utf-8-*-

import re, sys, json
import MySQLdb

reload(sys)
sys.setdefaultencoding('utf-8')


from app.models import *
from app import app

config = app.config

class Inception(object):
    def __init__(self):
        try:
            self.inception_host = config.get('INCEPTION_HOST')
            self.inception_port = int(config.get('INCEPTION_PORT'))
            
            self.inception_remote_backup_host = config.get('INCEPTION_REMOTE_BACKUP_HOST')
            self.inception_remote_backup_port = int(config.get( 'INCEPTION_REMOTE_BACKUP_PORT'))
            self.inception_remote_backup_user = config.get('INCEPTION_REMOTE_BACKUP_USER')
            self.inception_remote_backup_password = config.get( 'INCEPTION_REMOTE_BACKUP_PASSWORD')
        except AttributeError as a:
            print("Error: %s" % a)
        except ValueError as v:
            print("Error: %s" % v)
        
    def criticalDDL(self, sqlContent):
        '''
        识别DROP DATABASE, DROP TABLE, TRUNCATE PARTITION, TRUNCATE TABLE等高危DDL操作，因为对于这些操作，inception在备份时只能备份METADATA，而不会备份数据！
        如果识别到包含高危操作，则返回“审核不通过”
        '''
        if re.match(r"([\s\S]*)drop(\s+)database(\s+.*)|([\s\S]*)drop(\s+)table(\s+.*)|([\s\S]*)truncate(\s+)partition(\s+.*)|([\s\S]*)truncate(\s+)table(\s+.*)", sqlContent.lower()):
            return (('', '', 2, '', '不能包含【DROP DATABASE】|【DROP TABLE】|【TRUNCATE PARTITION】|【TRUNCATE TABLE】关键字！', '', '', '', '', ''),)
        else:
            return None

    def sqlautoReview(self, sqlContent, dbConfigName, isBackup=False):
        '''
        将sql交给inception进行自动审核，并返回审核结果。
        '''
        dbConfig=DbConfig.query.filter(DbConfig.name == dbConfigName).first()
        if not dbConfig:
            print("Error: 数据库配置不存在")
        dbHost = dbConfig.host
        dbPort = dbConfig.port
        dbUser = dbConfig.user
        dbPassword = dbConfig.password

        #这里无需判断字符串是否以；结尾，直接抛给inception enable check即可。
        #if sqlContent[-1] != ";":
            #sqlContent = sqlContent + ";"
        criticalddl=config.get('CRITICAL_DDL_ON_OFF')
        if criticalddl == "ON" :
            criticalDDL_check = self.criticalDDL(sqlContent)
        else:
            criticalDDL_check = None
        if criticalDDL_check is not None:
            result = criticalDDL_check
        else:
            sql = "/*--user=%s;--password=%s;--host=%s;--enable-check=1;--port=%s;*/\
              inception_magic_start;\
              %s\
              inception_magic_commit;" % (dbUser, dbPassword, dbHost, str(dbPort), sqlContent)
            result = self._fetchall(sql, self.inception_host, self.inception_port, '', '', '')

        return result
        
    def executeFinal(self, work):
        '''
        将sql交给inception进行最终执行，并返回执行结果。
        '''
        print work.db_config
        dbConfig = DbConfig.query.filter(DbConfig.name == work.db_config).first()
        if not dbConfig:
            print("Error: 数据库配置不存在")
        dbHost = dbConfig.host
        dbPort = dbConfig.port
        dbUser = dbConfig.user
        dbPassword = dbConfig.password


        strBackup = ""
        if work.backup == True:
            strBackup = "--enable-remote-backup;"
        else:
            strBackup = "--disable-remote-backup;"

        #根据inception的要求，执行之前最好先split一下
        sqlSplit = "/*--user=%s; --password=%s; --host=%s; --enable-execute;--port=%s; --enable-ignore-warnings;--enable-split;*/\
             inception_magic_start;\
             %s\
             inception_magic_commit;" % (dbUser, dbPassword, dbHost, str(dbPort), work.sql_content)
        splitResult = self._fetchall(sqlSplit, self.inception_host, self.inception_port, '', '', '')
        tmpList = []
        #对于split好的结果，再次交给inception执行.这里无需保持在长连接里执行，短连接即可. 
        for splitRow in splitResult:
            sqlTmp = splitRow[1]
            sqlExecute = "/*--user=%s;--password=%s;--host=%s;--enable-execute;--port=%s; --enable-ignore-warnings;%s*/\
                    inception_magic_start;\
                    %s\
                    inception_magic_commit;" % (dbUser, dbPassword, dbHost, str(dbPort), strBackup, sqlTmp)
                    
            executeResult = self._fetchall(sqlExecute, self.inception_host, self.inception_port, '', '', '')
            tmpList.append(executeResult)

        #二次加工一下，目的是为了和sqlautoReview()函数的return保持格式一致，便于在detail页面渲染.
        finalStatus = 0
        finalList = []
        for splitRow in tmpList:
            for sqlRow in splitRow:
                #如果发现任何一个行执行结果里有errLevel为1或2，并且stagestatus列没有包含Execute Successfully字样，则判断最终执行结果为有异常.
                if (sqlRow[2] == 1 or sqlRow[2] == 2) and re.match(r"\w*Execute Successfully\w*", sqlRow[3]) is None:
                    finalStatus = 3
                finalList.append(list(sqlRow))
        
        return (finalStatus, finalList)

    def getRollbackSqlList(self, workId):
        work = Work.query.filter(Work.id == workId).first()
        listExecuteResult = json.loads(work.execute_result)
        listBackupSql = []
        for row in listExecuteResult:
            #获取backup_dbname
            if row[8] == 'None':
                continue;
            backupDbName = row[8]
            sequence = row[7]
            opidTime = sequence.replace("'", "")
            sqlTable = "select tablename from %s.$_$Inception_backup_information$_$ where opid_time='%s';" % (backupDbName, opidTime)
            listTables = self._fetchall(sqlTable, self.inception_remote_backup_host, self.inception_remote_backup_port, self.inception_remote_backup_user, self.inception_remote_backup_password, '')
            if listTables is None or len(listTables) != 1:
                print("Error: returned listTables more than 1.")
            
            tableName = listTables[0][0]
            sqlBack = "select rollback_statement from %s.%s where opid_time='%s'" % (backupDbName, tableName, opidTime)
            listBackup = self._fetchall(sqlBack, self.inception_remote_backup_host, self.inception_remote_backup_port, self.inception_remote_backup_user, self.inception_remote_backup_password, '')
            if listBackup is not None and len(listBackup) !=0:
                for rownum in range(len(listBackup)):
                    listBackupSql.append(listBackup[rownum][0])
        return listBackupSql
            

    def _fetchall(self, sql, paramHost, paramPort, paramUser, paramPasswd, paramDb):
        '''
        封装mysql连接和获取结果集方法
        '''
        result = None
        conn = None
        cur = None
        sql = sql.encode('utf-8')

        try:
            conn=MySQLdb.connect(host=paramHost, user=paramUser, passwd=paramPasswd, db=paramDb, port=paramPort)
            conn.set_character_set('utf8')
            cur=conn.cursor()
            ret=cur.execute(sql)
            result=cur.fetchall()
            result=result
        except MySQLdb.Error as e:
            print("Mysql Error %d: %s" % (e.args[0], e.args[1]))
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()
        return result

