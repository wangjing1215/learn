# coding=utf-8
from core.libs import db
from web.utils import storage

class Model:
    def __init__(self, master=False, table=None, opration=False, mdb=None):
        self.mater = master
        DB = db.manager.master_core if master else db.manager.slave_core
        self.mdb = mdb or DB
        self.table = table
        if table is not None and opration:
            sql = """SELECT column_name as pri_key FROM INFORMATION_SCHEMA.`KEY_COLUMN_USAGE` WHERE table_name='{}' 
                  AND constraint_name='PRIMARY'""".format(self.table)
            rs = self.mdb.query(sql)
            self.pri_colnum = rs[0].pri_key if rs else None
        if opration and table is None:
            assert ValueError, 'TABLE CAN NOT BE NONE'

    # 通过唯一索引id查询结果
    def get_by_id(self, id):
        sql = "select * from {} where {} = {}".format(self.table, self.pri_colnum, id)
        rs = self.mdb.query(sql)
        return rs[0] if rs else 101

    def get_by_ids(self, idlist):
        result = {}
        ids = tuple(idlist)
        sql = "select * from {} where {} in {}".format(self.table, self.pri_colnum, ids)
        rs = self.mdb.query(sql)
        for i in rs:
            result[i[self.pri_colnum]] = i
        return result

    def select_with_count(self, where=None, what='*', add_condtion="", vars_value=None, sql_write=None):
        with self.mdb.transaction():
            if sql_write is not None:
                sql = sql_write
            else:
                if where is None:
                    sql = "select SQL_CALC_FOUND_ROWS {} from {} {}".format(what, self.table, add_condtion)
                else:
                    sql = "select SQL_CALC_FOUND_ROWS {} from {} where {} {}".format(what, self.table, where, add_condtion)
            rs = self.mdb.query(sql, vars=vars_value)
            count = self.mdb.query("select FOUND_ROWS() as count")[0].count
            reslut = storage({"sql_rs": rs, "count": count})
            return reslut

    def select(self, where=None, what='*', add_condtion="", vars_value=None, sql_write=None):
        if sql_write is not None:
            sql = sql_write
        else:
            if where is None:
                sql = "select  {} from {} {}".format(what, self.table, add_condtion)
            else:
                sql = "select SQL_CALC_FOUND_ROWS {} from {} where {} {}".format(what, self.table, where, add_condtion)
        rs = self.mdb.query(sql, vars=vars_value)
        return rs

    def update(self, set, where=None, vars_value=None):
        if where is None:
            sql = "update {} set {}".format(self.table, set)
        else:
            sql = "update {} set {} where {}".format(self.table, set, where)
        mdb = db.manager.master_core if not self.mater else self.mdb
        rs = mdb.query(sql, vars=vars_value)
        return rs

    @staticmethod
    def dict_to_str_update(data):
        op = ""
        for key, value in data.items():
            op = op + " {} = ${}".format(key, key) + ","
        op = op[:-1] if op != "" else ""
        if op == "":
            return 101
        else:
            return op

    def insert(self, colnum, values, vars_value=None):
        sql = "insert into {} ({}) values ({})".format(self.table, colnum, values)
        mdb = db.manager.master_core if not self.mater else self.mdb
        rs = mdb.query(sql, vars=vars_value)
        return rs

    @staticmethod
    def dict_to_str_insert(data):
        colnum = ""
        values = ""
        for key, value in data.items():
            colnum = colnum + key + ","
            values = values + "${}".format(key) + ","
        colnum = colnum[:-1] if colnum != "" else ""
        values = values[:-1] if values != "" else ""
        if colnum == "":
            return 101
        else:
            return storage({"colnum": colnum, "values": values})

    def insert_safe(self, colnum, values, vars_value=None):
        colnum_list = colnum.split(',')
        values_list = values.split(',')
        add_eq = ""
        for i, j in zip(colnum_list, values_list):
            add_eq = add_eq + "{}={}".format(i, j) + ","
        sql = "insert into {} ({}) values ({}) ON DUPLICATE KEY UPDATE {}".format(self.table, colnum, values, add_eq[:-1])
        print sql
        mdb = db.manager.master_core if not self.mater else self.mdb
        rs = mdb.query(sql, vars=vars_value)
        return rs

    def delete(self, conditions, vars_value=None):
        sql = "delete from {} where {}".format(self.table, conditions)
        mdb = db.manager.master_core if not self.mater else self.mdb
        rs = mdb.query(sql, vars=vars_value)
        return rs


class QureySave:
    def __init__(self, table, keycolnum, *args, **kwargs):
        self.values = storage()
        for key, value in kwargs.items():
            self.values[key] = value
        self.table = table
        self.keycolnum = keycolnum
        if keycolnum not in self.values.keys():
            assert KeyError, "keycolnum 没有对应值"

    def save(self):
        mdb = Model(table=self.table, master=True)
        set_str = mdb.dict_to_str_update(self.values)
        rs = mdb.update(set=set_str, where="{a} = ${a}".format(a=self.keycolnum), vars_value=self.values)
        return rs

    def hard_save(self):
        mdb = Model(table=self.table, master=True)
        set_str = mdb.dict_to_str_insert(self.values)
        rs = mdb.insert_safe(colnum=set_str.colnum, values=set_str["values"], vars_value=self.values)
        return rs
