import sqlite3
import configparser
from os.path import join,exists

config = configparser.ConfigParser()
config.read('config.ini')
if "DEFAULT" not in config or "workspaces" not in config['DEFAULT']:
    print("Invalid config file")
    exit()


class dbConn():
    __conn=None

    @classmethod
    def get(cls):
        if cls.__conn is None:
            print("Trying to use unconnected database")
            raise ValueError
        return cls.__conn

    @classmethod
    def connect(cls,workspace):
        if cls.__conn is not None:
            cls.__conn.close()
        dbPath = join(config['DEFAULT']['workspaces'],workspace,"workspace.db")
        if not exists(dbPath):
            print("Workspace database not found, the workspace must be corrupted !")
            raise ValueError
        cls.__conn = sqlite3.connect(dbPath)

    @classmethod
    def close(cls):
        cls.__conn.close()
        cls.__conn = None


