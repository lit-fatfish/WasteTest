import datetime
import json
import os
import platform
import shutil

import requests
import uuid
import threading
import time
from datetime import date
import redis
from redis import Redis
from threading import Timer




if platform.system() == 'Windows':
    config_name = os.path.join('config.json')
elif platform.system() == 'Linux':
    config_name = os.path.join('/opt','config.json')

# 根据键值读字符串
def get_values(r, key):
    dic = r.get(key)
    if dic :
        return eval(dic)
    else:
        return False

# dic 字典
def set_values(r, key, dic):
    json_data = read_jsonfile(config_name)
    r.set(key, str(dic),ex=int(json_data['expire'])*86400) # 获取到期天数，然后乘以86400s（一天）


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


def clear_file(r, path):
    json_data = read_jsonfile(config_name)
    timing = int(json_data["timing"]) * 86400
    num = int(json_data['expire'])

    if not os.path.exists(path):
        t = Timer(timing, clear_file, (r, path,))
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
                        # key-values 等待自动过期，删除成功或失败中的队列即可
                        if remove_queue(r,"finish_queue",video_name):
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
    t = Timer(timing, clear_file, (r, path,))
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
# rtsp_list 视频地址表
# cut_time 切片时间


def cut_video(r, list_num, rtsp_list, cut_time):
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
    rtsp_url = rtsp_list[list_num]["rtsp_url"].format(rtsp_list[list_num]["docker_ip"])  # 视频源地址
    print(rtsp_url)
    cmd = "ffmpeg -i " + rtsp_url + " -t " + interval + " -c copy -f mp4 -y " + filename
    print(cmd)
    val = os.system(cmd)
    print(val)

    # 判断视频是否存在，存在则上传
    if os.path.exists(filename):
        # 判断文件大小，0k的文件删除并且不写入到Redis
        if not os.path.getsize(filename):
            os.remove(filename)
            # 需要提前离开这个程序
            time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            log_str = "开始时间:" + str(time_start) + "\t\t结束时间:" + str(time_now) + "\t切片地址=" + rtsp_list[
                list_num] + "\t视频长度为0，切片失败\n"
            record_message("cut_result.log", log_str)
            # read_queue 默认读到的是第一个

            dic_status = get_values(r, rtsp_url)
            # 键值对存在的
            if dic_status:
                dic_status["fail_num"] += 1
                if dic_status["fail_num"] >= 5:
                    dic_status['status'] = 'fail'
            # 键值对不存在的,第一次就失败了
            else:
                dic_status = {
                    "num": list_num + 1,
                    "rtsp_url": rtsp_url,
                    "fail_num": 1,
                    "status": "normal"
                }

            # write_queue(r, "status_set", rtsp_url)  # 写入rtsp_url为集合的值
            set_values(r,rtsp_url, dic_status)
            return


        # 切片成功，记录日志
        time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_str = str(time_now) + "\t\t文件名=" + videoid + "\t切片成功\n"
        record_message("cut_result.log", log_str)
        run_time_str = "开始时间:" + str(time_start) + "\t\t结束时间:"+str(time_now) + "\t\t文件名=" + videoid + "\t\t花费时间=" + str(int(time.time()-start_time)) + "s\n"
        record_message("time.log",run_time_str)

        # 记录当前路的状态
        dic_status = {
            "num": list_num+1,
            "rtsp_url": rtsp_url,
            "fail_num": 0,
            "status": "normal"
        }
        # write_queue(r,"status_set",rtsp_url) # 写入rtsp_url为集合的值
        set_values(r,rtsp_url,dic_status)

        # 将数据写入等待队列
        # json_data = read_jsonfile('config.json')

        cameracode = rtsp_list[list_num]['cameracode']
        resultAddress = rtsp_list[list_num]['resultAddress']
        url = rtsp_list[list_num]['url']

        dic = {
            "filename": filename,
            "fail_num": 0,
            "url": url,
            "data_id": videoid,
            "cameracode": cameracode,
            "resultAddress": resultAddress,
            "time_start": str(time_now)
        }

        # 写入数据到字符串key-values  key为视频名，valus为字典
        # 记录视频名为队列
        set_values(r, videoid, dic)
        write_queue(r, "wait_queue", videoid)
    else:
        # 切片不成功
        time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_str = "开始时间:" + str(time_start) + "\t\t结束时间:"+str(time_now) + "\t切片地址=" + rtsp_url + "\t切片失败\n"
        record_message("cut_result.log", log_str)

        dic_status = get_values(r,rtsp_url)
        # 键值对存在的
        if dic_status:
            dic_status["fail_num"] += 1
            if dic_status["fail_num"] >= 5:
                dic_status['status'] = 'fail'
        # 键值对不存在的,第一次就失败了
        else:
            dic_status = {
                "num": list_num + 1,
                "rtsp_url": rtsp_url,
                "fail_num": 1,
                "status": "normal"
            }
        # write_queue(r, "status_set", rtsp_url)  # 写入rtsp_url为集合的值
        set_values(r, rtsp_url, dic_status)


# 将保存好的视频post到服务器
# 数据从Redis中读取


def post_to_server(r,queue_name):
    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 从Redis读取文件
    video_id = read_queue(r, queue_name)
    print(video_id)
    # 假如获取到的是一个字典，那获取键值对的时候，会出错，应该直接删除该队列
    if type(video_id) == type({}):
        remove_queue(r, queue_name, video_id)
        return
    if video_id:
        dic = get_values(r,video_id)
        print(dic)
        # 假如读取不到结果,删除该队列
        if not dic:
            remove_queue(r, queue_name, video_id)
            return
        # print(dic)
    else:
        # 读得到队列里面的内容，但是读取不到键值对，说明队列出现错误，应该删除当前的队列
        return
    print("hello1")
    # 这里字典是必定存在的，不存在的字典已经返回了
    filename = dic["filename"]
    fail_num = dic["fail_num"]
    url = dic["url"]
    formdata = {
        "videoid": dic["data_id"],
        "cameracode": dic["cameracode"],
        "resultAddress": dic["resultAddress"],
        "time_start": dic["time_start"]  # 需要校准
    }
    if os.path.exists(filename):
        files = {'fileData': open(filename, 'rb')}
    else:
        print("file can not found")
        return False
    print("hello2")
    try:
        response = requests.post(url, data=formdata, files=files)
        
        # exit(0)
        
        print(response)
        # 获取视频名
        # 移除当前等待队列
        # 删除对应的键
        print(response.status_code)
        remove_queue(r,queue_name,video_id)
        # remove_key(r,video_id) # 完成不用删除键值对的，重写会自动覆盖，只需要修改队列

        if response.status_code == 200:
            print("world")
            json_result = response.json()
            # 返回结果判断
            # 这里的data_id 采用从redis中读取文件名，因为有可能返回的json文件无法获得文件名
            post_result_str = str(time_now) + "\t\tdataid=" + dic["data_id"] + "\t\terror_code=" + str(
                json_result['error_code'])
            if json_result['error_code'] == 0:
                post_result_str += "\tpost成功\n"
                record_message('post_result.log', post_result_str)
                # 加入成功队列
                write_queue(r,"finish_queue",video_id)
                set_values(r,video_id,dic)
                return True
            # 错误码
            elif json_result['error_code'] == 10001:
                post_result_str += "\t非本机网点id" + "\tpost失败\n"
                dic["fail_num"] += 5
            elif json_result['error_code'] == 10002:
                post_result_str += "\t视频文件太小" + "\tpost失败\n"
                dic["fail_num"] += 5
            elif json_result['error_code'] == 10003:
                post_result_str += "\t视频文件太大" + "\tpost失败\n"
                dic["fail_num"] += 5
            elif json_result['error_code'] == 10009:
                post_result_str += "\t未在服务时间段" + "\tpost失败\n"
                dic["fail_num"] += 5
            elif json_result['error_code'] == 10011:
                post_result_str += "\t上传失败" + "\tpost失败\n"
            elif json_result['error_code'] == 10012:
                post_result_str += "\t重复上传" + "\tpost失败"
                # 删除文件和队列
                remove_queue(r,queue_name,dic["data_id"])  # 根据文件名删除队列
                # 文件是否删除，
                if os.path.exists(dic["filename"]):
                    os.remove(filename)
                return
            elif json_result['error_code'] == 10013:
                post_result_str += "\t缺少车道图	" + "\tpost失败"
                dic["fail_num"] += 5
            elif json_result['error_code'] == 10014:
                post_result_str += "\t视频缺少帧数	" + "\tpost失败"
                # 删除文件和队列
                remove_queue(r,queue_name,dic["data_id"])  # 根据文件名删除队列
                # 文件是否删除，
                if os.path.exists(dic["filename"]):
                    os.remove(filename)
                return
            record_message('post_result.log', post_result_str)
            # 这里肯定是失败的，次数+1
            dic["fail_num"] += 1

            # 上传错误代码到Redis
            dic_post = {
                "time": time_now,
                "data_id":dic["data_id"],
                "error_code":json_result['error_code']
            }
            key_post = 'fail' + dic["data_id"]
            set_values(r, key_post, dic_post)
            fail_num = dic["fail_num"]
            if fail_num >= 5:
                # 加入失败队列
                write_queue(r,"fail_queue",dic["data_id"])
            else:
                # 重新写到等待队列
                write_queue(r,"wait_queue",dic["data_id"])
            set_values(r, video_id, dic)
            return False
    # else:
    #     # 服务器返回的状态码不对，比如404之类的
    #     print("error")
    #     write_queue(r,"fail_queue",video_id)
    #     post_result_str = "服务器返回状态码：" + str(response.status_code) + "\n"
    #     record_message('post_result.log', post_result_str)
    #     return False
    # 没有成功执行默认判断为错误
    # 一般为服务器状态无响应，需要修改为失败队列，在后台等待上传，或者等待自动上传
    # 修改参数需要吗？还是直接加入失败队列。直接设置为失败队列就可以了
    # 加入失败队列
    except:
        write_queue(r,"fail_queue",video_id)
        # 上传错误代码到Redis
        dic_post = {
            "time": time_now,
            "data_id":dic["data_id"],
            "error_code":json_result['error_code']
        }
        key_post = 'fail' + dic["data_id"]
        set_values(r, key_post, dic_post)
        post_result_str = str(time_now) + "\t上传地址无响应\n"
        record_message('post_result.log', post_result_str)

# 上传到服务器线程

def post_thered(r, queue_name):

    t = threading.Thread(target=post_to_server, args=(r,queue_name,))
    t.start()


# 多线程启动
# redis 对象
# num = 一次启动多少个进程，
# numbers 启动的RTSP地址的下标
# rtsp_list RMTP地址下标
# cut_time 剪切时间


def thread_start(r, num, numbers, rtsp_list, cut_time):
    t_obj = []
    # 一次启动num个线程
    for i in range(num):
        t = threading.Thread(target=cut_video, args=(r,numbers - i - 1, rtsp_list, cut_time,))
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
    # docker不能存在主机名，因为需要部署到好多服务器
    if platform.system() == 'Windows':
        # host = '192.168.31.249'
        host = '127.0.0.1'
        pwd = ''
        db = 0
    elif platform.system() == 'Linux':
        host = 'redis'
        db = 0
    print(host)
    # host= 'localhost'
    # pwd=''
    redis_obj = Redis(host=host, port=6379, password=pwd, db=db,decode_responses=True)
    return redis_obj




def main():
    r = init_redis()
    clear_file(r,'log')
    clear_file(r,'video')
    post_fail_file(7200, r) # 每两小时运行一次
    while True:
        json_data = read_jsonfile(config_name)
        # print(json_data)
        if json_data['flag']:

            times = int(json_data['times'])
            numbers = len(json_data['rtsp_list'])
            cut_time = int(json_data['cut_time'])
            rtsp_list = json_data['rtsp_list']
            num = int( numbers/ times)  # 每分钟执行的个数
            if num >0:
                while((num * times) < numbers):
                    num += 1
            else:
                num = 1

            count = 0  # 秒计数清零
            # print('count=', count)
            # print('num', num)
            # print('cut_time', cut_time)
            # print('times', times)
            # print('numbers', numbers)
            # post_to_server(r, "wait_queue")

            for i in range(int(json_data['times']) * 60):
                # time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                # print(time_now)
                if count % 60 == 0:  # 每分钟执行一次
                    if numbers >= num:
                        # 执行num个并发，并把地址传进去
                        thread_start(r,num, numbers, rtsp_list, cut_time)
                        numbers = numbers - num
                    else:
                        if numbers > 0:
                            # 执行numbers个程序
                            thread_start(r, numbers, numbers, rtsp_list, cut_time)
                            numbers = 0

                count = count + 1
                # post到服务器
                # post_thered(r, "wait_queue")
                # if (i%10 ==0):
                    # post_thered(r, "wait_queue")
                post_to_server(r, "wait_queue")

                time.sleep(1)
        else:
            time.sleep(1)
            print('cut video program is not running')


if __name__ == "__main__":
    main()

