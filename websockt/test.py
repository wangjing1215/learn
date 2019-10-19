from db import db
import uuid
uniq_id = str(uuid.uuid1())
rs = db.query("""insert into msg (msg_uuid, send_user_id, recv_user_id, msg, create_time, status,status_remark) values
             ('{}',1, 2,"123", 32, 1,"232")""".format(uniq_id))
print(uniq_id)
rs_t = db.select("msg", where="msg_uuid='{}'".format(uniq_id))
print(rs_t[0])