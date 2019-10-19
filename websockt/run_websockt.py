import time
import asyncio
import json
import logging
import websockets
from db import db
import uuid


# 程序储存值
class websocket_data:
    STATE = {"value": 0}
    USERS = set()
    users = {}

    def state_event(self):
        return json.dumps({"type": "state", "pub": "在线满一个小时送一万"})

    def users_event(self):
        return json.dumps({"type": "users", "login": "ok"})

    def msg_event(self, send_user, recv_user, msg, msg_id=0):
        title = "{} > {}:{}".format(send_user, recv_user, msg)
        return json.dumps({"type": "msg", "msg": title, "msg_id": msg_id})


# 用户
class user:
    def __init__(self, user_id=None):
        self.user_id = user_id

    async def register(self, websocket):
        if self.user_id == None:
            websocket_data.USERS.add(websocket)
        else:
            websocket_data.users[self.user_id] = websocket
            user_name = self.user_id
            rs = db.select("msg", where="recv_user_id = $user_name and status=0", vars=locals())
            for i in rs:
                send_user = i.send_user_id
                recive_user = i.recv_user_id
                msg = i.msg
                id = i.msg_id
                await  WebSockt(websocket=websocket).re_send(send_user, recive_user, data=msg, msg_id=id)
                # 更新消息发送状态 检测到用户登录 补发未发送消息
                rs = db.query("""update msg set status = 1 where msg_id = $id""", vars=locals())

    # 系统消除客户端（断开连接或刷新）
    async def unregister(self, websocket):
        websocket_data.USERS.remove(websocket)
        user_id = list(websocket_data.users.keys())[list(websocket_data.users.values()).index(websocket)]
        await self.logout(user_id)

    # 用户登出（刷新或登录其他账号）
    async def logout(self, user_id):
        print(user_id, 'is logout')
        websocket_data.users.pop(user_id)



class WebSockt:
    def __init__(self, ip=None, port=None, websocket=None):
        self.use_ip = ip if ip != None else "0.0.0.0"
        self.use_port = port if port != None else 6789
        self.websocket = websocket if websocket != None else None
        self.user_id = 0

    # 开始函数
    def run(self):
        start_server = websockets.serve(self.recive, self.use_ip, self.use_port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    # 发送函数
    async def send(self, send_user="sys", recv_user=0, data=" ", msg_id=None):
        if recv_user == 0:
            await self.websocket.send(websocket_data().msg_event("sys", recv_user, data))
        else:
            await websocket_data.users[recv_user].send(websocket_data().msg_event(send_user, recv_user, data, msg_id=msg_id))

    # 消息重发
    async def re_send(self, send_user_id, recv_user, data, msg_id):
        await self.websocket.send(websocket_data().msg_event(send_user_id, recv_user, data, msg_id=msg_id))

    # 发送消息到所有存活客户端
    async def send_pub(self, data=""):
        await self.websocket.send(data)

    # 用户已读回调
    async def user_read(self, id):
        rs = db.query("""update msg set is_read = 1 where msg_id = $id""", vars=locals())

    # 记录函数
    def record(self, send_user=0, recv_user=0, msg="", status=1, status_remark=" "):
        now = int(time.time())
        msg_uuid = str(uuid.uuid1())
        if send_user != 0 and recv_user != 0 and msg != "":
            rs = db.query("""insert into msg (send_user_id, recv_user_id, msg, create_time, status,status_remark, 
            msg_uuid) values ($send_user, $recv_user,$msg, $now, $status,$status_remark, $msg_uuid)""", vars=locals())
            msg_rs = db.select("msg", where="msg_uuid = $msg_uuid", what="msg_id", vars=locals())
            msg_id = msg_rs[0].msg_id
            return msg_id

    # 接收函数
    async def recive(self, websocket, path):
        self.websocket = websocket
        # 登录会话注册
        await user().register(websocket)
        print(websocket_data.USERS)
        try:
            # 发送公告信息
            await self.send_pub(data=websocket_data().state_event())
            async for message in websocket:
                data = json.loads(message)
                # 登录
                if "user_name" in data:
                    if self.user_id != 0:
                        # 同一通信过程 先退出已登录者
                        if websocket in websocket_data.users.values():
                            user_id = list(websocket_data.users.keys())[list(websocket_data.users.values()).index(websocket)]
                            # 同一页面 其他人登录获得发送权
                            await user().logout(user_id)
                    user_name = data["user_name"]
                    await user(user_name).register(websocket)
                    self.user_id = user_name
                    print(websocket_data.users)
                # 向其他用户发送消息
                if "msg" in data and "recive_user" in data and "send_user" in data:
                    msg = data["msg"]
                    send_user = data["send_user"]
                    recive_user = data["recive_user"]
                    if recive_user in websocket_data.users.keys():
                        msg_id = self.record(send_user, recive_user, msg)
                        await self.send(send_user, recive_user, msg, msg_id=msg_id)
                    else:
                        self.record(send_user, recive_user, msg, 0, "用户离线")
                        await self.send(recv_user=send_user, data="用户离线")
                # 消息已读回调
                if "is_read" in data and "msg_id" in data:
                    await self.user_read(data["msg_id"])

        finally:
            await user().unregister(websocket)


