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

list = [
    "rtsp://anlly.godping.com:554/miku",
    "rtmp://rtmp01open.ys7.com/openlive/0fc24386798246288e41fc3af1ac347c",
    "rtmp://rtmp01open.ys7.com/openlive/61a15bf06f5342a1b7ca111a6c351b48",
    "rtmp://rtmp01open.ys7.com/openlive/bfb19a2adf27466db0d1a89f59c15dd1",
    "rtmp://rtmp01open.ys7.com/openlive/f3aee2d16cc1455e880954035f354a94",
    "rtmp://rtmp.open.ys7.com/openlive/126ddc556132429d81e2d03fa194f5f6",
    "rtmp://rtmp01open.ys7.com/openlive/55b81869b7e148dcaad306c6f11e083e",
    "rtmp://rtmp01open.ys7.com/openlive/1b3d536c3d3e4ef6bf9af5adb520f76c",
    "rtmp://rtmp01open.ys7.com/openlive/0c9b4a8cf8884e329111c302fa59ba7f",
    "rtmp://rtmp01open.ys7.com/openlive/8a73937b77db48fd843d4c05527b4ef3",
    "rtmp://rtmp.open.ys7.com/openlive/01eba7b3afe74844b8d84f543e474b1e",
    "rtmp://rtmp01open.ys7.com/openlive/75969ce2bf1e463ab1a17bb7dabecc06",
    "rtmp://rtmp01open.ys7.com/openlive/16bcf769d1734a0696144f5ec92743ca",
    "rtmp://rtmp01open.ys7.com/openlive/b2a480624c354cfdae69a873859f71a7",
    "rtmp://rtmp.open.ys7.com/openlive/a3afaf8b74614301b55507e596f282dc",
    "rtmp://rtmp.open.ys7.com/openlive/cbe546d4d8e44f0fb9282cae4b8d0b62",
    "rtmp://rtmp01open.ys7.com/openlive/0d896bf6b0e84c018e30733d674656f8",
    "rtmp://rtmp01open.ys7.com/openlive/68d83e3e5e3c4106b2f859d87d8874d4",
    "rtmp://rtmp.open.ys7.com/openlive/3131010c595344a2bef6c6c756cca9fd",
    "rtmp://rtmp01open.ys7.com/openlive/c889eba9c10a4c458e6c8a0dd459fd61",
    "rtmp://rtmp01open.ys7.com/openlive/821d1e0fe86b430790658961812bbaf8",
    "rtmp://rtmp01open.ys7.com/openlive/9e5f328748eb46e6ac8316785feccafb",
    "rtmp://rtmp.open.ys7.com/openlive/519b62be1df64cde84568e549b044f70",
    "rtmp://rtmp01open.ys7.com/openlive/c36d6957deca44f188dbe9f430fbfe8d",
    "rtmp://rtmp01open.ys7.com/openlive/a96b65f9d1fc475f9e8ceeb7f1a6c04d",
    "rtmp://rtmp01open.ys7.com/openlive/7dc88acc5d1449ce9a495f2331ae3e83",
    "rtmp://rtmp01open.ys7.com/openlive/56630f876e2b4b8d86679ad324707dfe",
    "rtmp://rtmp01open.ys7.com/openlive/26d39af86a8143f08a3bfc66756f921a",
    "rtmp://rtmp01open.ys7.com/openlive/decc164dc15943eaa1967b93dc15060f",
    "rtmp://rtmp01open.ys7.com/openlive/dcb454da50534813b3d3641fe58d38ff"
]


# 获取源视频，并保存在本地，最后Post到服务器上， num为输入的视频源 
def post_to_server(rtmp_url, cut_time):
    # 发送CMD命令，并保存视频到本地
    interval = str(cut_time)  # 录制多少时间
    videoid = ''.join(str(uuid.uuid4()).split('-'))  # videoid 采用uuid 并去掉括号 
    # 根据日期创建文件夹
    foldername = os.path.join('./video', str(date.today()))
    if not os.path.exists(foldername):
        os.mkdir(foldername)
    # filename = ".\\video\\" + videoid + '.mp4'
    filename = os.path.join(foldername, videoid + '.mp4')
    cmd = "ffmpeg -i " + rtmp_url + " -t " + interval + " -c copy -f mp4 -y " + filename
    val = os.system(cmd)
    print(val)

    # print("什么时候打印这个") #在执行完毕后才会打印这个函数
    # 判断视频是否存在，存在则上传
    # if os.path.exists(filename):
    #     # 将保存好的视频post到服务器
    #     url = "http://192.168.31.19/bsd/Handle.php"
    #
    #     formdata = {
    #         "videoid": videoid,
    #         "cameracode": "1",
    #         "resultAddress": "https://power.anlly.net/customer/api/v1/callback",
    #     }
    #
    #     files = {'fileData': open(filename, 'rb')}
    #     response = requests.post(url, data=formdata, files=files)
    #     json = response.json()
    #
    #     # 返回结果判断
    #     # 记录视频地址
    #     str1 = rtmp_url + '\n'
    #     record_message("time.txt", str1)
    #     record_error_code(json['error_code'])
    #     if json['error_code'] == 0:
    #         print(videoid + " ok!")
    #     else:  # 错误码...
    #         print(videoid + " error!")
    # else:
    #     print("文件不存在")


# post_to_server(0)


# 多线程启动
# num = 一次启动多少个进程，
# n = 调用那6路RTMP去获取视频  0=0-5 , 1 = 6-11, 2 = 12-17 3 = 18-23, 4 = 24-29 
# 
def thread_start(num, n):
    start_time = time.time()
    t_obj = []
    # 一次启动6个线程
    for i in range(num):
        t = threading.Thread(target=post_to_server, args=(n * num + i,))
        t_obj.append(t)
        t.start()

    for t in t_obj:
        t.join()

    cost_time = int(time.time() - start_time)
    # record_time(cost_time)
    time_now = datetime.datetime.now()
    str1 = str(time_now) + "    run time = " + str(cost_time) + "s\n"
    record_message("time.txt", str1)
    # print("cost  :" ,time.time()-start_time)


def thread_start1(rtmp_url, cut_time):
    start_time = time.time()
    t = threading.Thread(target=post_to_server, args=(rtmp_url,cut_time,))
    t.start()
    # t.join()
    cost_time = int(time.time() - start_time)
    time_now = datetime.datetime.now()
    str1 = str(time_now) + "    run time = " + str(cost_time) + "s\n"
    record_message("time.txt", str1)


# thread_start(6, 0)


# 重写一个写入文件
def record_message(filename, str):
    with open(filename, 'a+') as fp:
        fp.write(str)


# 写个文件，进程的时间记录下来
def record_time(time_lenght):
    with open("time.txt", 'a+') as fp:
        time_now = datetime.datetime.now()
        fp.write(str(time_now) + "    run time = " + str(time_lenght) + "s\n")


def record_error_code(error_code):
    with open("errorcode.txt", 'a+') as fp:
        time_now = datetime.datetime.now()
        fp.write(str(time_now) + "    error = " + str(error_code) + "\n")


def read_jsonfile(filename):
    with open(filename, 'r', encoding='utf8')as fp:
        json_data = json.load(fp)
        return json_data


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
            count = 0 # 秒计数清零
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
            count = 0 # 秒计数清零
            print('count=',count)
            print('num', num)
            print('cut_time', cut_time)
            print('times', times)
            print('numbers', numbers)
            for i in range(int(json_data['times']) * 60):
                # times分钟内把所有路运行完
                # num = int(int(json_data['numbers']) / int(json_data['times'])) #一分钟需要多少路
                #
                if count % 60 == 0:  # 每分钟执行一次
                    for j in range(num):
                        if numbers > 0:
                            numbers = numbers - 1
                            thread_start1(rtmp_list[numbers], cut_time)
                            print(str(numbers) + ":" + rtmp_list[numbers])

                count = count + 1
                time.sleep(1)
        else:
            time.sleep(1)
            print('cut video program is not running')


if __name__ == "__main__":
    main1()
