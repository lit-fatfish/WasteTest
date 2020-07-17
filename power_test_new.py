import json
import os
import requests
import uuid
import threading
import time
from datetime import date
import redis


# 根据键值读字符串
def get_values(r, key):
    return eval(r.get(key))

# dic 字典
def set_values(r, key, dic):
    r.set(key, str(dic))


def remove_key(r, key):
    r.delete(key)


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


# 获取源视频，并保存在本地，并记录到Redis
# list_num 列表的下标
# rtmp_list 视频地址表
# cut_time 切片时间


def cut_video(r, list_num, rtmp_list, cut_time):
    # 发送CMD命令，并保存视频到本地
    start_time = time.time()
    interval = str(cut_time)  # 录制多少时间
    videoid = ''.join(str(uuid.uuid4()).split('-'))  # videoid 采用uuid 并去掉括号 
    # 根据日期创建文件夹
    foldername = os.path.join('video', str(date.today()))
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
        log_str = str(time_now) + "\t文件名=" + videoid + "\t切片成功\n"
        record_message("cut_result.log", log_str)
        run_time_str = str(time_now) + "\t\t文件名=" + videoid + "\t\t花费时间=" + str(int(time.time()-start_time)) + "s\n"
        record_message("time.log",run_time_str)

        # 记录当前路的状态
        dic_status = {
            "num": list_num+1,
            "rtmp_url": rtmp_list[list_num],
            "status": "fail"
        }
        # 移除失败的
        remove_queue(r,"status_queue",dic_status)
        dic_status["status"] = "normal"
        write_queue(r,"status_queue",dic_status)

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
        log_str = str(time_now) + "\t切片地址=" + rtmp_list[list_num] + "\t切片失败\n"
        record_message("cut_result.log", log_str)
        dic_status = {
            "num": list_num + 1,
            "rtmp_url": rtmp_list[list_num],
            "status": "normal"
        }
        remove_queue(r, "status_queue", dic_status)
        dic_status["status"] = "fail"
        write_queue(r, "status_queue", dic_status)

# 将保存好的视频post到服务器
# 数据从Redis中读取


def post_to_server(r):
    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 从Redis读取文件
    video_id = read_queue(r, "wait_queue")
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
    remove_queue(r,"wait_queue",video_id)
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
        post_result_str = "服务器返回状态码：" + response.status_code + "\n"
        record_message('post_result.log', post_result_str)


# 上传到服务器线程

def post_thered(r):
    t = threading.Thread(target=post_to_server, args=(r,))
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

# 写入信息到文件


def record_message(filename, str):
    with open(filename, 'a+', encoding='utf8') as fp:
        fp.write(str)


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
    pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)  # host是redis主机，需要redis服务端和客户端都启动 redis默认端口是6379G
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
                post_thered(r)
                time.sleep(1)
        else:
            time.sleep(1)
            print('cut video program is not running')


if __name__ == "__main__":
    main()

