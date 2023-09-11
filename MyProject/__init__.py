import pymysql
import ssl
import certifi
print(certifi.where())
pymysql.install_as_MySQLdb()
ssl._create_default_https_context = ssl._create_unverified_context
