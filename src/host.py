import sqlite3
import json
from src.params import dbConn


class Host():
    def __init__(self,name,uname,issue,machineId,macs):
        self.name = name
        self.id = None
        self.uname = uname
        self.issue = issue
        self.machineId = machineId
        self.macs = macs
        c = dbConn.get().cursor()
        c.execute('SELECT id FROM hosts WHERE name=? AND uname=? AND issue=? AND machineid=? AND macs=?',(self.name,self.uname,self.issue,self.machineId,json.dumps(self.macs)))
        savedHost = c.fetchone()
        c.close()
        if savedHost is not None:
            self.id = savedHost[0]

    def getId(self):
        return self.id

    def getName(self):
        return self.name

    def getUname(self):
        return self.uname

    def getIssue(self):
        return self.issue

    def getMachineId(self):
        return self.machineId

    def getMacs(self):
        return self.macs

    def getClosestEndpoint(self):
        from src.path import Path
        endpoints = self.getEndpoints()
        shortestLen = None
        shortest = None
        for endpoint in endpoints:
            if Path.hasDirectPath(endpoint):
                return endpoint
            chain = Path.getPath(None,endpoint)
            if shortestLen is None or len(chain) < shortestLen:
                shortest = endpoint
                shortestLen = len(chain)
        return shortest

    def getEndpoints(self):
        from src.endpoint import Endpoint
        endpoints = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT ip,port FROM endpoints WHERE host=?',(self.id,)):
            endpoints.append(Endpoint(row[0],row[1]))
        c.close()
        return endpoints

    def save(self):
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the host is already saved in the database : UPDATE
            c.execute('''UPDATE hosts 
                SET
                    name = ?,
                    uname = ?,
                    issue = ?,
                    machineid = ?,
                    macs = ?
                WHERE id = ?''',
                (self.name, self.uname, self.issue, self.machineId, json.dumps(self.macs), self.id))
        else:
            #The host doesn't exists in database : INSERT
            c.execute('''INSERT INTO hosts(name,uname,issue,machineid,macs)
                VALUES (?,?,?,?,?) ''',
                (self.name,self.uname,self.issue,self.machineId,json.dumps(self.macs)))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM hosts WHERE name=? AND uname=? AND issue=? AND machineid=? AND macs=?',(self.name,self.uname,self.issue,self.machineId,json.dumps(self.macs)))
            self.id = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    @classmethod
    def findAll(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT id FROM hosts'):
            ret.append(Host.find(row[0]))
        c.close()
        return ret

    @classmethod
    def find(cls,hostId):
        c = dbConn.get().cursor()
        c.execute('''SELECT name,uname,issue,machineId,macs FROM hosts WHERE id=?''',(hostId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Host(row[0],row[1],row[2],row[3],json.loads(row[4]))

    @classmethod
    def findByName(cls,name):
        c = dbConn.get().cursor()
        hosts = []
        for row in c.execute('''SELECT id FROM hosts WHERE name=?''',(name,)):
            hosts.append(Host.find(row[0]))
        c.close()
        return hosts

    @classmethod
    def findAllNames(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT name FROM hosts'):
            ret.append(row[0])
        c.close()
        return ret


    def __str__(self):
        return self.name

