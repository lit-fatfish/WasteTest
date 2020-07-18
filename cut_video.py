import datetime
import json
import os
import shutil

import requests
import uuid
import threading
import time
from datetime import date
import redis
from redis import Redis
from threading import Timer

# 根据键值读字符串
def get_values(r, key):
    return eval(r.get(key))

# dic 字典
def set_values(r, key, dic):
    r.set(key, str(dic))


# 成功返回int 1
def remove_key(r, key):
    return r.delete(key)


# callback_obj字典对象
def write_queue(r,queue_name, callback_obj):
    callback_obj = json.dumps(callback_obj)
    callback_mapping = {
        callback_obj: time.time()
    }
    r.zadd(queue_name, callback_mapping)


def read_queue(r,queue_name):
    range_list = r.zrange(queue_name, 0, 1)
    if range_list:
        set_del_task = range_list[0]
        set_del_task = json.loads(set_del_task)
        return set_del_task


def remove_queue(r,queue_name, callback_obj):
    callback_obj = json.dumps(callback_obj)
    r.zrem(queue_name,callback_obj)


def get_days_list(num):
    list_days = []
    today = date.today()
    for i in range(num):
        day = datetime.timedelta(i)
        list_days.append(str(today-day))
    return list_days



# 定时清除文件
# timing = 定时时长s
# r = redis
# path 基于程序位置的文件夹
# num 保留天数
# 其中当video目录删除文件时，会根据文件名去删除Redis缓存队列中的数据


def clear_file(timing,r, path, num):
    if not os.path.exists(path):
        t = Timer(timing, clear_file, (timing, path, num,))
        t.start()
        return
    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    list_days = get_days_list(num)
    list = os.listdir(path)
    list_rm = []
    for filename in list:
        if filename not in list_days:
            # 文件名不在列表中
            list_rm.append(filename)
            filename = os.path.join(path,filename)
            if os.path.isdir(filename):

                # 判断清理文件是否是视频文件
                if path == 'video':
                    list_video = os.listdir(filename)
                    for video_name in list_video:
                        video_name = video_name[0:-4] # 去掉.mp4 ，得到视频名
                        # 删除key-values
                        # 删除成功才说明存在Redis中
                        if remove_key(r,video_name):
                            # 删除队列
                            if remove_queue(r,"finish_queue",video_name):
                                pass
                            elif remove_queue(r,"wait_queue",video_name):
                                pass
                            elif remove_queue(r,"fail_queue",video_name):
                                pass
                                # 删除文件夹
                shutil.rmtree(filename)
            elif os.path.isfile(filename):
                # 删除文件
                os.remove(filename)
    str_clear = str(time_now) + "\t\t路径："+path + "\t\t文件名=" + str(list_rm)+ "\n"
    record_message("clear.log",str_clear)
    t = Timer(timing, clear_file, (timing, r,path, num,))
    t.start()


# 定时上传失败队列中的文件


def post_fail_file(timing,r):
    # 读取全部的失败队列
    # 假如不存在，则返回
    # 读取到的是一个文件名，根据文件名去读取数据
    # 根据读取到的数据进行post
    list_filename = r.zrange("fail_queue", 0, -1) # 获取全部的队列，根据这个队列进行循环上传
    if list_filename:
        for filename in list_filename:
            post_to_server(r,"fail_queue") #从失败队列中取出数据post到服务器
            time.sleep(1)
    t = Timer(timing, post_fail_file,(timing,r,))
    t.start()

# 写入信息到文件


def record_message(filename, message_str):
    if not os.path.exists('log'):
        os.mkdir("log")
    path = os.path.join('log', str(date.today()))
    if not os.path.exists(path):
        os.mkdir(path)
    filename = os.path.join(path,filename)
    with open(filename, 'a+', encoding='utf8') as fp:
        fp.write(message_str)

# 获取源视频，并保存在本地，并记录到Redis
# list_num 列表的下标
# rtmp_list 视频地址表
# cut_time 切片时间


def cut_video(r, list_num, rtmp_list, cut_time):
    # 发送CMD命令，并保存视频到本地
    start_time = time.time()
    time_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    interval = str(cut_time)  # 录制多少时间
    videoid = ''.join(str(uuid.uuid4()).split('-'))  # videoid 采用uuid 并去掉括号
    if not os.path.exists('video'):
        os.mkdir("video")
    # 根据日期创建文件夹
    foldername = os.path.join('.','video', str(date.today()))
    if not os.path.exists(foldername):
        os.mkdir(foldername)
    filename = os.path.join(foldername, videoid + '.mp4')
    cmd = "ffmpeg -i " + rtmp_list[list_num] + " -t " + interval + " -c copy -f mp4 -y " + filename
    val = os.system(cmd)
    print(val)

    # 判断视频是否存在，存在则上传
    if os.path.exists(filename):
        # 切片成功，记录日志
        time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_str = str(time_now) + "\t\t文件名=" + videoid + "\t切片成功\n"
        record_message("cut_result.log", log_str)
        run_time_str = "开始时间:" + str(time_start) + "\t\t结束时间:"+str(time_now) + "\t\t文件名=" + videoid + "\t\t花费时间=" + str(int(time.time()-start_time)) + "s\n"
        record_message("time.log",run_time_str)

        # 记录当前路的状态
        dic_status = {
            "num": list_num+1,
            "rtmp_url": rtmp_list[list_num],
            "fail_num": 0,
            "status": "normal"
        }
        write_queue(r,"status_queue",rtmp_list[list_num]) # 写入rtmp_url为集合的值
        set_values(r,rtmp_list[list_num],dic_status)

        # remove_queue(r,"status_queue",dic_status)
        # dic_status["status"] = "normal"
        # write_queue(r,"status_queue",dic_status)

        # 将数据写入队列
        json_data = read_jsonfile('config.json')

        dic = {
            "filename": filename,
            "fail_num": 0,
            "url": json_data['url'],
            "data_id": videoid,
            "cameracode": json_data['cameracode'],
            "resultAddress": json_data['resultAddress'],
            "time_start": str(time_now)
        }

        # 写入数据到字符串key-values  key为视频名，valus为字典
        # 记录视频名为队列
        set_values(r, videoid, dic)
        write_queue(r, "wait_queue", videoid)
    else:
        # 切片不成功
        time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_str = "开始时间:" + str(time_start) + "\t\t结束时间:"+str(time_now) + "\t切片地址=" + rtmp_list[list_num] + "\t切片失败\n"
        record_message("cut_result.log", log_str)
        rtmp_url = read_queue(r, "status_queue")
        if rtmp_url:
            dic_status = get_values(r, rtmp_url)
        else:
            return
        dic_status["fail_num"] += 1
        if dic_status["fail_num"] >=5:
            dic_status['status'] = 'fail'

        write_queue(r, "status_queue", rtmp_list[list_num])  # 写入rtmp_url为集合的值
        set_values(r, rtmp_list[list_num], dic_status)


# 将保存好的视频post到服务器
# 数据从Redis中读取


def post_to_server(r,queue_name):
    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 从Redis读取文件
    video_id = read_queue(r, queue_name)
    if video_id:
        dic = get_values(r,video_id)
    else:
        return
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
    # 获取视频名
    # 移除当前等待队列
    # 删除对应的键
    remove_queue(r,queue_name,video_id)
    remove_key(r,video_id)

    if response.status_code == 200:
        json_result = response.json()
        # 返回结果判断
        post_result_str = str(time_now) + "\t\tdataid=" + json_result['dataid'] + "\t\terror_code=" + str(
            json_result['error_code'])
        if json_result['error_code'] == 0:
            post_result_str += "\tpost成功\n"
            record_message('post_result.log', post_result_str)
            # 加入成功队列
            write_queue(r,"finish_queue",video_id)
            set_values(r,video_id,dic)
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
        # 这里肯定是失败的，次数+！
        dic["fail_num"] += 1

        if fail_num >= 5:
            # 加入失败队列
            write_queue(r,"fail_queue",dic)
        else:
            # 重新写到等待队列
            write_queue(r,"wait_queue",dic)
        set_values(r, video_id, dic)
    else:
        # 服务器返回的状态码不对，比如404之类的
        post_result_str = "服务器返回状态码：" + str(response.status_code) + "\n"
        record_message('post_result.log', post_result_str)


# 上传到服务器线程

def post_thered(r, queue_name):
    t = threading.Thread(target=post_to_server, args=(r,queue_name,))
    t.start()


# 多线程启动
# redis 对象
# num = 一次启动多少个进程，
# numbers 启动的RTMP地址的下标
# rtmp_list RMTP地址下标
# cut_time 剪切时间


def thread_start(r, num, numbers, rtmp_list, cut_time):
    t_obj = []
    # 一次启动num个线程
    for i in range(num):
        t = threading.Thread(target=cut_video, args=(r,numbers - i - 1, rtmp_list, cut_time,))
        t_obj.append(t)
        t.start()



    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    str1 = str(time_now) + "\t 并发路数：" + str(num) + "\n"
    record_message("time.log", str1)




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


def init_redis():
    pwd = "anlly12345"
    host= '192.168.31.184'
    # host= 'localhost'
    # pwd=''
    redis_obj = Redis(host=host, port=6379, password=pwd, db=8,decode_responses=True)
    return redis_obj



def main():
    r = init_redis()
    clear_file(28800,r,'log',7) # 3600*8 = 28800 8个小时
    clear_file(28800,r,'video',7)
    post_fail_file(7200, r) # 每两小时运行一次
    while True:
        json_data = read_jsonfile('config.json')
        if json_data['flag'] == '1':

            times = int(json_data['times'])
            numbers = int(json_data['numbers'])
            cut_time = int(json_data['cut_time'])
            rtmp_list = json_data['RTMP_list']
            num = int((int(json_data['numbers']) + 1) / times)  # 每分钟执行的个数
            count = 0  # 秒计数清零
            # print('count=', count)
            # print('num', num)
            # print('cut_time', cut_time)
            # print('times', times)
            # print('numbers', numbers)
            for i in range(int(json_data['times']) * 60):
                time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                # print(time_now)
                if count % 60 == 0:  # 每分钟执行一次
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
                # post到服务器
                post_thered(r, "wait_queue")
                time.sleep(1)
        else:
            time.sleep(1)
            print('cut video program is not running')


if __name__ == "__main__":
    main()

