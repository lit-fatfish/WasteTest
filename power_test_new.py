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

# 获取源视频，并保存在本地，最后Post到服务器上， num为输入的视频源
# list_num 列表的下标
# rtmp_list 视频地址表
# cut_time 切片时间
def post_to_server(list_num, rtmp_list, cut_time):
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
        log_str = str(time_now) + "   文件名=" + videoid + "   切片成功\n"
        record_message("cut_result.log", log_str)
        # 将保存好的视频post到服务器
        # 读取配置文件
        json_data = read_jsonfile('config.json')

        url = json_data['url']
        formdata = {
            "videoid": videoid,
            "cameracode": json_data['cameracode'],
            "resultAddress": json_data['resultAddress'],
            "time_start": str(time_now)   #需要校准
        }
        files = {'fileData': open(filename, 'rb')}

        # print(url, formdata)
        response = requests.post(url, data=formdata, files=files)
        if response.status_code == 200:
            json_result = response.json()
            # 返回结果判断

            # record_error_code(json['error_code'])
            time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            post_result_str = str(time_now) + "    dataid=" + json_result['dataid'] + "   error_code=" + str(json_result['error_code'])
            if json_result['error_code'] == 0:
                post_result_str += "   post成功\n"

            # 错误码... 未添加错误代码处理
            elif json_result['error_code'] == 10001:
                # 非本机网点id
                post_result_str += "   非本机网点id" + "   post失败"
            elif json_result['error_code'] == 10002:
                # 视频文件太小
                post_result_str += "   视频文件太小" + "   post失败"
            elif json_result['error_code'] == 10003:
                # 视频文件太小
                post_result_str += "   视频文件太小" + "   post失败"
            elif json_result['error_code'] == 10009:
                # 视频文件太小
                post_result_str += "   视频文件太小" + "   post失败"
            elif json_result['error_code'] == 10011:
                # 视频文件太小
                post_result_str += "   视频文件太小" + "   post失败"
            elif json_result['error_code'] == 10012:
                # 重复上传（正在推理中）
                post_result_str += "   重复上传" + "   post失败"
            elif json_result['error_code'] == 10014:
                # 视频缺少帧数
                post_result_str += "   视频缺少帧数" + "   post失败"
            record_message('post_result.log', post_result_str)
        else:
            # 服务器返回的状态码不对，比如404之类的
            post_result_str = "服务器返回状态码：" + response.status_code + "\n"
            record_message('post_result.log', post_result_str)
    else:
        # 切片不成功
        time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_str = str(time_now) + "   切片地址=" + rtmp_list[list_num] + "   切片失败\n"
        record_message("cut_result.log", log_str)
        # print("文件不存在")


# post_to_server(0)


# 多线程启动
# num = 一次启动多少个进程，
# n = 调用那6路RTMP去获取视频  0=0-5 , 1 = 6-11, 2 = 12-17 3 = 18-23, 4 = 24-29 
# 
def thread_start(num, numbers, rtmp_list, cut_time):
    start_time = time.time()
    t_obj = []
    # 一次启动6个线程
    for i in range(num):
        t = threading.Thread(target=post_to_server, args=(numbers - i-1, rtmp_list, cut_time,))
        t_obj.append(t)
        t.start()

    for t in t_obj:
        t.join()

    cost_time = int(time.time() - start_time)
    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    str1 = str(time_now) + "    并发路数：" + str(num) + "    run time = " + str(cost_time) + "s\n"
    record_message("time.log", str1)
    # print("cost  :" ,time.time()-start_time)


def thread_start1(rtmp_url, cut_time):
    start_time = time.time()
    t = threading.Thread(target=post_to_server, args=(rtmp_url, cut_time,))
    t.start()
    # t.join()
    cost_time = int(time.time() - start_time)
    time_now = datetime.datetime.now()
    str1 = str(time_now) + "    run time = " + str(cost_time) + "s\n"
    record_message("time.txt", str1)


# thread_start(6, 0)


# 重写一个写入文件
def record_message(filename, str):
    with open(filename, 'a+', encoding='utf8') as fp:
        fp.write(str)



def record_error_code(error_code):
    with open("errorcode.txt", 'a+', encoding='utf8') as fp:
        time_now = datetime.datetime.now()
        fp.write(str(time_now) + "    error = " + str(error_code) + "\n")


def read_jsonfile(filename):
    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf8')as fp:
            json_data = json.load(fp)

            jsonfile_str = str(time_now) + "     文件名=" + filename + "    读取成功\n"
            record_message('jsonfile_result.log', jsonfile_str)
            return json_data
    else:
        # 文件名不存在，写入日志
        jsonfile_str = str(time_now) + "     文件名=" + filename + "    读取失败\n"
        record_message('jsonfile_result.log', jsonfile_str)
        return False





def main():
    # time_now = datetime.datetime.now()
    # thread_start(1, 0)
    while True:
        json_data = read_jsonfile('config.json')
        if json_data['flag'] == '1':
            times = int(json_data['times'])
            numbers = int(json_data['numbers'])
            cut_time = int(json_data['cut_time'])
            rtmp_list = json_data['RTMP_list']
            thread_interval_time = int((times * 60 * 0.8) / int(json_data['numbers']))
            count = 0  # 秒计数清零
            for i in range(int(json_data['times']) * 60):
                # times分钟内把所有路运行完
                # num = int(int(json_data['numbers']) / int(json_data['times'])) #一分钟需要多少路
                #
                if count % thread_interval_time == 0:
                    if numbers > 0:
                        numbers = numbers - 1
                        thread_start1(rtmp_list[numbers], cut_time)
                        print(str(numbers) + ":" + rtmp_list[numbers])

                # 休息时间为 if (300 - 60) / 30 = 8s
                count = count + 1
                time.sleep(1)
        else:
            time.sleep(1)
            print('cut video program is not running')


def main1():
    # time_now = datetime.datetime.now()
    # thread_start(1, 0)
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
                        thread_start(num, numbers, rtmp_list, cut_time)
                        numbers = numbers - num
                    else:
                        if numbers > 0:
                            # 执行numbers个程序
                            thread_start(numbers, numbers, rtmp_list, cut_time)
                            numbers = 0

                count = count + 1
                time.sleep(1)
        else:
            time.sleep(1)
            print('cut video program is not running')


if __name__ == "__main__":
    main1()
