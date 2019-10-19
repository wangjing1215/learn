import time
import asyncio
import json
import logging
import websockets
from db import db
logging.basicConfig()

STATE = {"value": 0}

USERS = set()
users = {}


def state_event():
    return json.dumps({"type": "state", "pub": "在线满一个小时送一万"})


def users_event():
    return json.dumps({"type": "users", "login": "ok"})


def msg_event(user_name, msg):
    return json.dumps({"type": "msg", "user_name": user_name, "msg": msg})


async def notify_state():
    if USERS:  # asyncio.wait doesn't accept an empty list
        message = state_event()
        await asyncio.wait([user.send(message) for user in USERS])


async def notify_users(user_id):
    if USERS:  # asyncio.wait doesn't accept an empty list
        message = users_event()
        user = users[str(user_id)]
        await user.send(message)


async def notify_to_user(send_user, recive_user, msg):
    now = int(time.time())
    try:
        user = users[str(recive_user)]
        message = msg_event(send_user, msg)
        await user.send(message)
        rs = db.query("""insert into msg (send_user_id, recv_user_id, msg, create_time, status) values ($send_user, 
                $recive_user,$msg, $now, 1)""", vars=locals())
    except:
        user = users[send_user]
        message = msg_event("系统提示", "该用户已离线，消息会在他登录后发送")
        await asyncio.wait([user.send(message)])
        rs = db.query("""insert into msg (send_user_id, recv_user_id, msg, create_time, status, status_remark) values 
        ($send_user,$recive_user,$msg, $now, 0, "该用户已离线")""", vars=locals())


# 重发
async def re_notify_to_user(send_user, recive_user, msg, id):
    now = int(time.time())
    try:
        user = users[str(recive_user)]
        message = msg_event(send_user, msg)
        await user.send(message)
        rs = db.query("""update msg set status = 1 where msg_id = $id""", vars=locals())
    except:
        rs = db.query("""update msg set status = 2 where msg_id = $id""", vars=locals())


async def notify_all_users(send_user, msg):
    try:
        message = msg_event(send_user, msg)
        await asyncio.wait([user.send(message) for user in USERS])
    except:
        pass


async def register(websocket, user_name=None):
    if user_name == None:
        USERS.add(websocket)
    else:
        users[user_name] = websocket
        rs = db.select("msg", where="recv_user_id = $user_name and status=0", vars=locals())
        for i in rs:
            send_user = i.send_user_id
            recive_user = i.recv_user_id
            msg = i.msg
            id = i.msg_id
            await re_notify_to_user(send_user, recive_user, msg, id)
        await notify_users(user_name)


async def unregister(websocket):
    USERS.remove(websocket)
    # await notify_users()


def consumer(websocket, message):
    print(websocket.remote_address, message, STATE["value"])


async def consumer_handler(websocket, path):
    async for message in websocket:
        consumer(message)


async def producer_handler(websocket, path):
    while True:
        # message = await producer()
        # await websocket.send(message)
        pass


async def counter(websocket, path):
    # register(websocket) sends user_event() to websocket
    await register(websocket)
    try:
        # await consumer_handler(websocket, path)
        await websocket.send(state_event())
        async for message in websocket:
            data = json.loads(message)
            if "user_name" in data:
                user_name = data["user_name"]
                await register(websocket, user_name)
            if "msg" in data and "recive_user" in data:
                msg = data["msg"]
                send_user = data["send_user"]
                recive_user = data["recive_user"]
                print(data)
                await notify_to_user(send_user, recive_user, msg)
            await notify_state()

            # consumer(websocket, message)
    finally:
        await unregister(websocket)


def websockt_run():
    start_server = websockets.serve(counter, "localhost", 6789)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    websockt_run()