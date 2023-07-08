import websockets
import asyncio
import signal
import random
import logging
import json

pool = []
DESK = 0
sign = ["♠", "♥", "♦", "♣"]
AIlist = ["三哥", "李二狗", "MR.C", "王麻子"]
LINK = {}
TABLE = []
STATUS = "wait"
DESKMAX = None
MAXMONEY = 0
LEVEL = 0
RICH = 300
POVERTY = 50
WORK_LOCK = asyncio.Lock()


def clearDesk():
    global DESK
    global DESKMAX
    global MAXMONEY
    global LEVEL
    global TABLE
    for user in TABLE:
        user["push"] = 0
        user["pass"] = 0
        user["master"] = 0
        user["pool"] = []
        user["status"] = "wait"
    TABLE = []
    DESK = 0
    DESKMAX = None
    MAXMONEY = 0
    LEVEL = 0
    changeStatus("wait")


def changeStatus(val):
    global STATUS
    STATUS = val


def check_json(input_str):
    try:
        json.loads(input_str)
        return True
    except:
        return False


def makeSms(type, data=None):
    return json.dumps({"type": type, "data": data}, ensure_ascii=False)


async def userSend(user, type, data=None):
    if user["ai"]:
        return
    await send(user["socket"], type, data)


async def send(websocket, type, data=None):
    await websocket.send(makeSms(type, data))


def broadcast(msg, type="broadcast"):
    connected = set()
    for user in TABLE:
        if user["ai"]:
            continue
        connected.add(user["socket"])
    websockets.broadcast(connected, makeSms(type, msg))


def broadcastLink(msg, type="broadcast"):
    connected = set()
    for id in LINK:
        user = LINK[id]
        connected.add(user["socket"])
    websockets.broadcast(connected, makeSms(type, msg))


def choice():
    global pool
    index = random.randint(0, len(pool) - 1)
    return pool.pop(index)


def shuffle():
    global pool
    pool = []
    for item in sign:
        i = 0
        while i < 13:
            i += 1
            if i == 1:
                show = "A"
            elif i == 11:
                show = "J"
            elif i == 12:
                show = "Q"
            elif i == 13:
                show = "K"
            else:
                show = str(i)
            pool.append(item + show)
    return pool


def initAI():
    index = random.randint(0, len(AIlist) - 1)
    element = AIlist[index]
    return {
        "uid": random.randrange(10000, 20000),
        "name": element,
        "ai": True,
        "money": random.randrange(1000, 2000),
        "pool": [],
        "joke": "",
        "master": 1,
        "push": 0,
        "pass": 0,
    }


def initUser(websocket, uid):
    return {
        "uid": uid,
        "socket": websocket,
        "name": "某个不换mj的扑街",
        "ai": False,
        "money": 1000,
        "pool": [],
        "joke": "",
        "status": "",
        "master": 0,
        "push": 0,
        "pass": 0,
    }


def checkPoint(userPool):
    point = 0
    for item in userPool:
        item = item[1:3]
        if item == "A":
            item = 1
        elif item in ["J", "Q", "K"]:
            item = 10
        point += int(item)
    return point


async def checkStatus():
    type = "want" if STATUS == "money" else "want"

    passNum = 0
    bad = 0
    for user in TABLE:
        if user["status"] in ["pass", "bad", "show"]:
            passNum += 1
        if user["status"] == "bad":
            bad += 1
    if len(TABLE) - bad == 1:
        changeStatus("show")
        return await allShowHand()

    if passNum == len(TABLE) and STATUS not in ["walk", "show", "win"]:
        changeStatus("walk")
        await walk(type)


async def money(user, data):
    if "money" != STATUS or "money" != user["status"]:
        return await userSend(user, "tip", "不是加注的时候")
    try:
        data = abs(int(data))
    except ValueError:
        data = 10

    global DESK
    user["status"] = "pass"
    if user["money"] - data < 0:
        data = user["money"]
        user["status"] = "show"
        await userSend(user, "nomoney")
    user["push"] += data
    global DESKMAX
    global MAXMONEY

    if DESKMAX == None:
        DESKMAX = user["uid"]
        MAXMONEY = data
    elif data > MAXMONEY:
        DESKMAX = user["uid"]
        MAXMONEY = data
    broadcast("{} 加注：{}$".format(user["name"], data))
    user["money"] -= data
    DESK += data
    await checkStatus()


async def masterKill(data):
    for user in TABLE:
        if user["master"] == 1:
            user["money"] += int(data)
            await userSend(user, "tip", "收割了一个散户，血赚 {}$".format(data))


async def want(user):
    if "want" != STATUS or "want" != user["status"]:
        return await userSend(user, "tip", "不是叫牌的时候")
    global DESK
    async with WORK_LOCK:
        if len(pool) == 0:
            return False
        ele = choice()
        user["pool"].append(ele)
        user["status"] = "pass"
        await userSend(user, "hand", user["pool"])
        broadcast("〖{}〗高调的叫了一张牌：{}，接下来让我们看看他什么时候会爆掉~".format(user["name"], ele))
        point = checkPoint(user["pool"])
        if point > 21:
            user["status"] = "bad"
            if user["master"] != 1:
                DESK -= user["push"]
                await masterKill(user["push"])
                broadcast("〖{}〗高调的叫牌之后，居然马上就爆了，庄家血赚一个亿呀".format(user["name"]))
    await checkStatus()


async def show(user):
    if user["status"] in ["show", "bad", "money"]:
        return await userSend(user, "tip", "不是showHand的时候")
    user["status"] = "show"
    broadcast("{} 已经准备开牌大杀四方了".format(user["name"]))
    await checkStatus()


async def waitMaster():
    # 如果状态已经被切走则不处理
    if "master" == STATUS:
        changeStatus("first")
        TABLE.append(initAI())
        await deal()


async def waitMoney():
    # 如果状态已经被切走则不处理
    if "money" == STATUS:
        changeStatus("walk")
        await walk("want")


async def waitWant():
    # 如果状态已经被切走则不处理
    if "want" == STATUS:
        changeStatus("walk")
        await walk("money")


async def allShowHand():
    if STATUS != "show":
        return
    changeStatus("win")
    global DESK
    win = None
    max = 0
    last = None
    for user in TABLE:
        if user["status"] == "bad":
            continue
        point = checkPoint(user["pool"])
        if win == None:
            win = user
            max = point
        elif win["master"] == 1 and point >= max:
            win = user
            max = point
        elif point > max:
            win = user
            max = point
    print("【win】", win, DESK)
    win["money"] += DESK
    DESK = 0
    poolLen = len(win["pool"])
    hand = "，".join(win["pool"][0:poolLen])
    msg = desktop(True)
    broadcast(msg, "deal")
    await asyncio.sleep(0.5)
    broadcast("最后还是技高人胆大的{} 凭借 {} 秒杀了一众宵小".format(win["name"], hand), "win")
    changeStatus("wait")
    clearDesk()


async def checkWin():
    show = 0
    exists = 0
    for user in TABLE:
        if user["status"] in ["show", "bad"]:
            show += 1
        else:
            exists += 1
    if show == len(TABLE) or exists == 1:
        changeStatus("show")
        return await allShowHand()


async def walk(type):
    if STATUS != "walk":
        print("【walk被锁定】")
        return
    show = 0
    for user in TABLE:
        if user["status"] == "pass":
            user["status"] = type
        elif user["status"] not in ["show", "bad"]:
            user["status"] = type
            user["pass"] += 1
            await userSend(user, "tip", "你超时了自动pass {}".format(STATUS))
            if user["pass"] > 3:
                user["status"] = "show"

        if user["status"] in ["show", "bad"]:
            show += 1
    if show == len(TABLE):
        changeStatus("show")
        return await allShowHand()
    global DESKMAX
    global MAXMONEY
    global LEVEL
    LEVEL += 1
    changeStatus(type)
    if type == "want":
        for user in TABLE:
            if user["uid"] == DESKMAX:
                broadcast("本轮〖{}〗凭借 {}的高注，秒杀了在座的各位".format(user["name"], MAXMONEY))

    DESKMAX = None
    MAXMONEY = 0

    msg = desktop()
    broadcast(msg, "deal")
    await asyncio.sleep(1)
    broadcast(None, type)


async def userPass(user):
    if STATUS not in ["money", "want"]:
        return await userSend(user, "tip", "别瞎pass")
    if user["status"] not in ["money", "want"]:
        return await userSend(user, "tip", "别瞎pass")
    user["status"] = "pass"
    broadcast("〖{}〗勇敢的选择了pass".format(user["name"]))
    await checkStatus()


async def bad(user):
    if STATUS not in ["money", "want"]:
        return await userSend(user, "tip", "别瞎bad")
    if user["status"] not in ["money", "want"]:
        return await userSend(user, "tip", "别瞎bad")
    user["status"] = "bad"
    broadcast("〖{}〗灰溜溜的盖住了牌".format(user["name"]))
    await checkStatus()


def desktop(show=False):
    msg = ""
    for user in TABLE:
        poolLen = len(user["pool"])
        master = "【庄家】" if user["master"] == 1 else "【散户】"
        userM = "【巨有钱的瘪犊子】" if user["money"] > RICH else ""
        userM = "【这么点钱回家搅奶粉去吧】" if user["money"] < POVERTY else ""

        if user["status"] == "bad":
            kill = "【弃牌】"
            hand = "，".join(user["pool"][0:poolLen])
        else:
            kill = ""
            hand = "底牌，" + "，".join(user["pool"][1:poolLen])
        if show:
            hand = "，".join(user["pool"][0:poolLen])
        msg += "〖{}〗{}{}{}  现在的手牌：{}\r\n".format(
            user["name"], master, kill, userM, hand
        )
    msg += "\r\n\r\n【桌上堆了】{}$".format(DESK)
    return msg


# 发牌
async def deal():
    shuffle()
    global DESK
    for user in TABLE:
        ele = choice()
        user["pool"].append(ele)
        ele = choice()
        user["pool"].append(ele)
        user["money"] -= 10
        user["push"] += 10
        DESK += 10
        user["status"] = "money"
        await userSend(user, "hand", user["pool"])
    msg = desktop()
    # 推送牌局状态
    broadcast(msg, "deal")
    changeStatus("money")
    broadcast(None, "money")


async def userMaster(user):
    async with WORK_LOCK:
        if "master" == STATUS:
            changeStatus("first")
            user["master"] = 1
            await userSend(user, "tip", "叫庄成功")
            # 流程推进
            await deal()
        else:
            await userSend(user, "tip", "叫庄失败，被某个瘪犊子抢庄了")


async def ready(user):
    if "wait" != STATUS:
        return await userSend(user, "tip", "当前有对局未结束，请稍后，新一局开始后将马上为您接入")
    user["status"] = "wait"
    async with WORK_LOCK:
        exists = []
        for user in TABLE:
            exists.append(user["uid"])
        for id in LINK:
            if user["status"] == "wait" and id not in exists:
                TABLE.append(user)

    if len(TABLE) > 1:
        if "master" != STATUS:
            changeStatus("master")
            broadcast(None, "master")
    else:
        return await userSend(user, "tip", "目前没有其他人在线，请稍等，或者输入：ai()，开始和ai对局")


async def ai():
    if "wait" == STATUS:
        TABLE.append(initAI())
        await deal()

async def message_handler(message, websocket):
    if check_json(message):
        message = json.loads(message)
        data = message["data"] if "data" in message else None
        type = message["type"]
        socket_id = websocket.id
        if socket_id in LINK:
            user = LINK[socket_id]
        else:
            user = initUser(websocket, socket_id)

        if "init" == type:
            print("【init】")
            LINK[socket_id] = user
            await send(websocket, "init")
            user["status"] = "init"
        elif "name" == type:
            user["name"] = str(data)
            await send(websocket, "name", "改名成功，尊敬的：" + user["name"])
        elif "ready" == type:
            print("【ready】", user)
            user["status"] = "ready"
            await ready(user)
        elif "master" == type:
            print("【master】", user)
            await userMaster(user)
        elif "want" == type:
            print("【want】", user)
            await want(user)
        elif "money" == type:
            print("【money】", user)
            await money(user, data)
        elif "pass" == type:
            print("【pass】", user)
            await userPass(user)
        elif "bad" == type:
            print("【bad】", user)
            await bad(user)
        elif "show" == type:
            print("【show】", user)
            await show(user)
        elif "ai" == type:
            await ai();
        elif "now" == type:
            await userSend(user, "tip", "你还剩：{}$".format(user["money"]))
        elif "broadcast" == type:
            print("【broadcast】", data)
            broadcast(data)
        elif "stop" == type:
            print("结束")
        else:
            print("【等待关闭】")
            await websocket.wait_closed()
    else:
        print(message)


def aiWin(point):
    yes = 21 - point
    rand = random.randrange(1, 21)
    return rand > yes


async def aiMoney():
    for user in TABLE:
        if not user["ai"]:
            continue
        if user["status"] != "money":
            break
        print("aiMoney", user)
        point = checkPoint(user["pool"])
        if aiWin(point):
            await money(user, 100)
        else:
            await userPass(user)
        break


async def aiWant():
    for user in TABLE:
        if not user["ai"]:
            continue
        if user["status"] != "want":
            break
        point = checkPoint(user["pool"])
        print("aiWant", user)
        if point >= 17:
            await show(user)
        elif not aiWin(point):
            await want(user)
        else:
            await userPass(user)
        break


def sleep(type, time):
    if type == STATUS:
        time += 0.5
    else:
        type = STATUS
        time = 0
    return type, time


async def watch():
    type = None
    time = 0
    while True:
        await asyncio.sleep(1)
        type, time = sleep(type, time)
        if STATUS == "master":
            if time > 30:
                await waitMaster()
        elif STATUS == "money":
            await aiMoney()
            if time > 30:
                await waitMoney()
        elif STATUS == "want":
            await aiWant()
            if time > 30:
                await waitWant()


async def handler(websocket):
    print("【id】", websocket.id)
    try:
        async for message in websocket:
            print(message)
            await message_handler(message, websocket)
    except websockets.exceptions.ConnectionClosed as e:
        print("【连接断开】", e.rcvd.code, websocket.id)
        if 1000 == e.rcvd.code:
            logging.warning("【服务端断开】")
        elif 1005 == e.rcvd.code:
            logging.warning("【客户端断开】")
        if websocket.id in LINK:
            LINK.pop(websocket.id)
            for index, user in enumerate(TABLE):
                if user["uid"] == websocket.id:
                    TABLE.pop(index)
                    broadcast("{} 掉线了".format(user["name"]))
        if len(LINK) == 0:
            clearDesk()
        # 清理进程
    except Exception as e:
        logging.exception(e)
    print("【触发循环结束】")


async def main():
    # Set the stop condition when receiving SIGTERM.
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    asyncio.create_task(watch())
    async with websockets.serve(
        handler,
        host="",
        port=8765,
        reuse_port=True,
    ):
        await stop


if __name__ == "__main__":
    asyncio.run(main())
