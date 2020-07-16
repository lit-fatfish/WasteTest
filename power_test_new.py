# 主要用来测试CPU和内存的性能

# 测试 开1路/2/4/6/10 时CPU的性能
# 一直开着6路时，内存是否会一直增加

# 本程序用测试1路/2/4/6/10 时CPU的性能
import json
import os
import requests
import datetime
import uuid
import threading
import time
from datetime import date
import redis

def write_queue(r,queue_name, callback_obj):
    callback_obj = json.dumps(callback_obj)
    callback_mapping = {
        callback_obj: time.time()
    }
    r.zadd(queue_name, callback_mapping)



# 返回整个数据的字典


def read_queue(r,queue_name):
    range_list = r.zrange(queue_name, 0, 1)
    if range_list:
        set_del_task = range_list[0]
        set_del_task = json.loads(set_del_task)
        return set_del_task


def remove_queue(r,queue_name, callback_obj):
    callback_obj = json.dumps(callback_obj)
    r.zrem(queue_name,callback_obj)


# def write_queue(r, queue_name, list):
#     if len(list) == 7:
#         if r.rpush(queue_name, list[0], list[1], list[2], list[3], list[4], list[5], list[6]):
#             return True
#         else:
#             time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
#             redis_str = str(time_now) + "\twrite_queue fail\t" + str(list) + "\n"
#             record_message("redis.log", redis_str)
#             return False
#     else:
#         return False
#
#
# def read_queue(r, queue_name):
#     list = r.lrange(queue_name, 0, 6)
#     if len(list) == 7:
#         return list
#     else:
#         # 读不到，应该是列表为空，不用记录日志
#         # time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
#         # redis_str = str(time_now) + "\tread_queue fail\t" + "\n"
#         # record_message("redis.log", redis_str)
#          return False
#
# def remove_queue(r, queue_name):
#     if r.ltrim("queue_name", 7, -1):
#         return True
#     else:
#         time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
#         redis_str = str(time_now) + "\tremove_queue fail\t" + "\n"
#         record_message("redis.log", redis_str)
#         return False


# 获取源视频，并保存在本地，最后Post到服务器上， num为输入的视频源
# list_num 列表的下标
# rtmp_list 视频地址表
# cut_time 切片时间


def cut_video(r, list_num, rtmp_list, cut_time):
    # 发送CMD命令，并保存视频到本地
    interval = str(cut_time)  # 录制多少时间
    videoid = ''.join(str(uuid.uuid4()).split('-'))  # videoid 采用uuid 并去掉括号 
    # 根据日期创建文件夹
    foldername = os.path.join('video', str(date.today()))
    if not os.path.exists(foldername):
        os.mkdir(foldername)
    # filename = ".\\video\\" + videoid + '.mp4'
    filename = os.path.join(foldername, videoid + '.mp4')
    cmd = "ffmpeg -i " + rtmp_list[list_num] + " -t " + interval + " -c copy -f mp4 -y " + filename
    val = os.system(cmd)
    print(val)

    # print("什么时候打印这个") #在执行完毕后才会打印这个函数
    # 判断视频是否存在，存在则上传
    if os.path.exists(filename):
        # 切片成功，记录日志
        time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_str = str(time_now) + "\t文件名=" + videoid + "\t切片成功\n"
        record_message("cut_result.log", log_str)
        # 将数据写入队列
        json_data = read_jsonfile('config.json')

        # redis 返回的就是列表，暂时就先按这样的顺序，在使用的时候，也按这样的顺序存储
        # list_temp = []
        # list_temp.append(filename)
        # list_temp.append("0")  # 失败次数
        # list_temp.append(json_data['url'])
        # list_temp.append(videoid)
        # list_temp.append(json_data['cameracode'])
        # list_temp.append(json_data['resultAddress'])
        # list_temp.append(str(time_now))
        dic = {
            "filename": filename,
            "fail_num": 0,
            "url": json_data['url'],
            "data_id": videoid,
            "cameracode": json_data['cameracode'],
            "resultAddress": json_data['resultAddress'],
            "time_start": str(time_now)
        }

        write_queue(r, "wait_queue", dic)

    else:
        # 切片不成功
        time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_str = str(time_now) + "\t切片地址=" + rtmp_list[list_num] + "\t切片失败\n"
        record_message("cut_result.log", log_str)
        # print("文件不存在")


def post_to_server(r):
    # 将保存好的视频post到服务器
    # 从Redis读取文件
    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    dic = read_queue(r, "wait_queue")
    if dic:
        filename = dic["filename"]
        fail_num = dic["fail_num"]
        url = dic["url"]
        formdata = {
            "videoid": dic["data_id"],
            "cameracode": dic["cameracode"],
            "resultAddress": dic["resultAddress"],
            "time_start": dic["time_start"]  # 需要校准
        }
        files = {'fileData': open(filename, 'rb')}
    else:
        return False
    response = requests.post(url, data=formdata, files=files)
    # 移除当前等待队列
    # print(remove_queue(r, "wait_queue"))
    # r.lpop("wait_queue")
    # r.lpop("wait_queue")
    # r.lpop("wait_queue")
    # r.lpop("wait_queue")
    # r.lpop("wait_queue")
    # r.lpop("wait_queue")
    # r.lpop("wait_queue")
    remove_queue(r,"wait_queue",dic)

    if response.status_code == 200:
        json_result = response.json()
        # 返回结果判断
        post_result_str = str(time_now) + "\tdataid=" + json_result['dataid'] + "\terror_code=" + str(
            json_result['error_code'])
        if json_result['error_code'] == 0:
            post_result_str += "\tpost成功\n"
            record_message('post_result.log', post_result_str)
            # 加入成功队列
            write_queue(r,"finish_queue",dic)

            return True
        # 错误码... 未添加错误代码处理
        elif json_result['error_code'] == 10001:
            # 非本机网点id
            post_result_str += "\t非本机网点id" + "\tpost失败"
        elif json_result['error_code'] == 10002:
            # 视频文件太小
            post_result_str += "\t视频文件太小" + "\tpost失败"
        elif json_result['error_code'] == 10003:
            # 视频文件太小
            post_result_str += "\t视频文件太小" + "\tpost失败"
        elif json_result['error_code'] == 10009:
            # 视频文件太小
            post_result_str += "\t视频文件太小" + "\tpost失败"
        elif json_result['error_code'] == 10011:
            # 视频文件太小
            post_result_str += "\t视频文件太小" + "\tpost失败"
        elif json_result['error_code'] == 10012:
            # 重复上传（正在推理中）
            post_result_str += "\t重复上传" + "\tpost失败"
        elif json_result['error_code'] == 10014:
            # 视频缺少帧数
            post_result_str += "\t视频缺少帧数" + "\tpost失败"
        record_message('post_result.log', post_result_str)

        if fail_num >= 4:
            # 加入失败队列
            dic["fail_num"] += 1
            write_queue(r,"fail_queue",dic)

        else:
            dic["fail_num"] += 1
            write_queue(r,"wait_queue",dic)
            # 失败次数+1 并重新写到等待队列
    else:
        # 服务器返回的状态码不对，比如404之类的
        post_result_str = "服务器返回状态码：" + response.status_code + "\n"
        record_message('post_result.log', post_result_str)


# 上传到服务器线程

def post_thered(r):
    t = threading.Thread(target=post_to_server, args=(r,))
    t.start()


# 多线程启动
# num = 一次启动多少个进程，
# numbers 启动的RTMP地址的下标
# rtmp_list RMTP地址下标
# cut_time 剪切时间
def thread_start(r,num, numbers, rtmp_list, cut_time):
    start_time = time.time()
    t_obj = []
    # 一次启动6个线程
    for i in range(num):
        t = threading.Thread(target=cut_video, args=(r,numbers - i - 1, rtmp_list, cut_time,))
        t_obj.append(t)
        t.start()

    for t in t_obj:
        t.join()

    cost_time = int(time.time() - start_time)
    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    str1 = str(time_now) + "\t 并发路数：" + str(num) + "\trun time = " + str(cost_time) + "s\n"
    record_message("time.log", str1)
    # print("cost  :" ,time.time()-start_time)


# thread_start(6, 0)


# 重写一个写入文件
def record_message(filename, str):
    with open(filename, 'a+', encoding='utf8') as fp:
        fp.write(str)


def record_error_code(error_code):
    with open("errorcode.txt", 'a+', encoding='utf8') as fp:
        time_now = datetime.datetime.now()
        fp.write(str(time_now) + "\terror = " + str(error_code) + "\n")


def read_jsonfile(filename):
    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf8')as fp:
            json_data = json.load(fp)

            jsonfile_str = str(time_now) + "\t文件名=" + filename + "\t读取成功\n"
            record_message('jsonfile_result.log', jsonfile_str)
            return json_data
    else:
        # 文件名不存在，写入日志
        jsonfile_str = str(time_now) + "\t文件名=" + filename + "\t读取失败\n"
        record_message('jsonfile_result.log', jsonfile_str)
        return False


def main():
    # time_now = datetime.datetime.now()
    # thread_start(1, 0)
    pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)  # host是redis主机，需要redis服务端和客户端都启动 redis默认端口是6379G
    while True:
        json_data = read_jsonfile('config.json')
        if json_data['flag'] == '1':

            times = int(json_data['times'])
            numbers = int(json_data['numbers'])
            cut_time = int(json_data['cut_time'])
            rtmp_list = json_data['RTMP_list']
            num = int(int(json_data['numbers']) / times)  # 每分钟执行的个数
            count = 0  # 秒计数清零
            print('count=', count)
            print('num', num)
            print('cut_time', cut_time)
            print('times', times)
            print('numbers', numbers)
            for i in range(int(json_data['times']) * 60):
                time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                print(time_now)
                # times分钟内把所有路运行完
                # num = int(int(json_data['numbers']) / int(json_data['times'])) #一分钟需要多少路
                #
                if count % 60 == 0:  # 每分钟执行一次
                    # 假如现存路数大于等于一分钟并发路数
                    # 执行当前的num数个，并且将numbers减num个
                    # 否则
                    # 判断numbers是否>0
                    # 大于0执行numbers个程序，然后清0
                    # 注意，numbers对应着RTMP地址，开始修改

                    if numbers >= num:
                        # 执行num个并发，并把地址传进去
                        thread_start(r,num, numbers, rtmp_list, cut_time)
                        numbers = numbers - num
                    else:
                        if numbers > 0:
                            # 执行numbers个程序
                            thread_start(r, numbers, numbers, rtmp_list, cut_time)
                            numbers = 0

                count = count + 1
                post_thered(r)
                time.sleep(1)
        else:
            time.sleep(1)
            print('cut video program is not running')


def main1():
    pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    # post_thered(r)
    post_to_server(r)

if __name__ == "__main__":
    main()

