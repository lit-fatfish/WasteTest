import os
import redis
import requests
from flask import Flask, render_template, request, jsonify
import json
import time
import platform
from flask_cors import CORS

from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, supports_credentials=True)  # 跨域

# @app.route('/')
# def index():
#     return render_template('home.html')
# 根据键值读字符串
def get_values(r, key):
    dic = r.get(key)
    if dic :
        return eval(dic)
    else:
        return dic


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


def read_first_queue(r,queue_name):
    range_list = r.zra0nge(queue_name, 0, 1)
    if range_list:
        set_del_task = range_list[0]
        set_del_task = json.loads(set_del_task)
        return set_del_task


def read_all_queue(r,queue_name,num):
    range_list = r.zrange(queue_name, 0, num)
    # print(range_list)
    list = []
    if range_list:
        for data in range_list:
            if type(data) != type({}):
                set_del_task = json.loads(data)
                list.append(set_del_task)
        # print(list)
        return list
    else:
        return False


def read_queue(r,queue_name,start,end):
    range_list = r.zrange(queue_name, start, end,desc=True) # 按照倒序查找
    # print(range_list)
    list = []
    if range_list:
        for data in range_list:
            if type(data) != type({}):
                set_del_task = json.loads(data)
                list.append(set_del_task)
        # print(list)
        return list
    else:
        return False

def remove_queue(r,queue_name, callback_obj):
    callback_obj = json.dumps(callback_obj)
    r.zrem(queue_name,callback_obj)


def read_queue_num(r, queue_name):
    length = r.zcard(queue_name)
    return length


def init_redis():
    pwd = "anlly12345"
    # docker不能存在主机名，因为需要部署到好多服务器
    if platform.system() == 'Windows':
        # host = '192.168.31.249'
        host = '127.0.0.1'
        pwd = ""
        db = 0
    elif platform.system() == 'Linux':
        host = 'redis'
        db = 0
    # host = 'localhost'
    # pwd = ''
    redis_obj = redis.Redis(host=host, port=6379, password=pwd, db=db, decode_responses=True)
    return redis_obj


def read_jsonfile(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf8')as fp:
            json_data = json.load(fp)

            return json_data
    else:
        # 文件名不存在，写入日志
        print("文件不存在")
        return False

@app.route('/')
def home():
    return render_template('test.html')


@app.route('/finish_list', methods=['GET', 'POST'])
def finish_list():

    dic = request.get_json()
    if not dic :
        return  jsonify(False)
    current_page = dic["current_page"]
    page_size = dic["page_size"]
    start = (current_page - 1) * page_size
    end = start + page_size - 1

    datas = read_queue(r,"finish_queue",start,end)

    if datas:
        list = []
        for data in datas:
            temp = get_values(r, data)
            list.append(temp)
        datas = list

    return jsonify(datas)  # 可以返回多个参数，返回后以数组的形式区分


@app.route('/wait_list', methods=['GET', 'POST'])
def wait_list():

    dic = request.get_json()
    if not dic :
        return  jsonify(False)
    print(dic)
    current_page = dic["current_page"]
    page_size = dic["page_size"]
    start = (current_page - 1) * page_size
    end = start + page_size - 1

    datas = read_queue(r, "wait_queue", start, end)

    if datas:
        list = []
        for data in datas:
            # print(data)
            if type(data) != type({}):
                temp = get_values(r, data)
                list.append(temp)
        datas = list

    return jsonify(datas)


@app.route('/fail_list', methods=['GET', 'POST'])
def fail_list():
    # r = init_redis()
    # r = redis.Redis(host='localhost', port=6379,db=8, decode_responses=True)
    # 获取到完成队列的列表
    # datas = r1.zrange("finish_queue",0,10)

    dic = request.get_json()
    if not dic :
        return  jsonify(False)
    current_page = dic["current_page"]
    page_size = dic["page_size"]
    start = (current_page - 1) * page_size
    end = start + page_size - 1

    datas = read_queue(r, "fail_queue", start, end)

    # print(datas)
    if datas:
        list = []
        for data in datas:
            # print(data)
            if type(data) != type({}):
                temp = get_values(r, data) # 获取到的temp是一个字典，把失败的状态码也给它返回去
                fail_str = 'fail'+data
                fail_dic = get_values(r,fail_str)
                if fail_dic:
                    temp['error_code'] = fail_dic['error_code']
                list.append(temp)
        datas = list

    return jsonify(datas)


@app.route('/queue_num', methods=['GET', 'POST'])
def queue_num():
    # 获取三个队列的数量


    dic = {}
    dic['finish_queue'] = read_queue_num(r,"finish_queue")
    dic["wait_queue"] = read_queue_num(r,"wait_queue")
    dic['fail_queue'] = read_queue_num(r,"fail_queue")

    return jsonify(dic)


@app.route('/clear_all', methods=['GET', 'POST'])
def clear_all():
    dic = request.get_json()
    if dic:
        queue_num = dic["queue_name"]
        remove_key(r,queue_num)
        return jsonify(True)
    else:
        return jsonify(False)

@app.route('/status',methods=['GET','POST'])
def status():
    if platform.system() == 'Windows':
        filename = os.path.join('D:', '\\Code', 'test','linux', 'config.json')
    elif platform.system() == 'Linux':
        filename = os.path.join('/','opt','config.json')
    dic = read_jsonfile(filename) # 获取json文件
    if dic:
        list = []
        for rtsp in dic["rtsp_list"]:
            rtsp_url = rtsp["rtsp_url"].format(rtsp["docker_ip"])
            temp = get_values(r, rtsp_url)
            if temp:
                list.append(temp)
        print(list)
        return jsonify(list)
    else:
        return jsonify(False)

    # datas = read_all_queue(r, "status_set", -1)
    # if datas:
    #     list = []
    #     for data in datas:
    #         temp = get_values(r, data)
    #         list.append(temp)
    #     return jsonify(list)
    # else:
    #     return jsonify(False)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # 获取上传到这里的文件名，然后读取键值对，去上传文件，并返回结果
    # 一个开始尝试
    # 通过文件名获取到字典，赋值带着参数去post，post结果考虑，
    # 首先post失败的才能进行重新上传，
    # post结果有成功和不成功，不成功的话就告诉不成功
    # post成功需要把失败队列里面的内容删掉，然后加成功队列，键值对不用更改
    # 关于状态，和失败次数，post成功后需要重新记录失败次数，还是不用
    # 后台上传不修改任何参数，最多修改在那个队列
    datas = {
        "success":0,
        "fail":0
    }
    dic = request.get_json()
    video_id = dic['data_id']
    dic = get_values(r,video_id)
    if dic:
        filename = dic["filename"]
        if not os.path.exists(filename):
            datas['fail'] += 1
            return jsonify(datas)
            # fail_num = dic["fail_num"]
        url = dic["url"]
        formdata = {
            "videoid": dic["data_id"],
            "cameracode": dic["cameracode"],
            "resultAddress": dic["resultAddress"],
            "time_start": dic["time_start"]  # 需要校准
        }
        files = {'fileData': open(filename, 'rb')}

        response = requests.post(url, data=formdata, files=files)
        if response.status_code == 200:
            json_result = response.json()
            # 这里的data_id 采用从redis中读取文件名，因为有可能返回的json文件无法获得文件名
            if json_result['error_code'] == 0:
                # 加入成功队列
                remove_queue(r, "fail_queue", video_id)
                write_queue(r, "finish_queue", video_id)
                datas['success'] += 1
            else:
                datas['fail'] += 1

        else:
            # 服务器返回的状态码不对，比如404之类的
            datas['fail'] += 1
    return jsonify(datas)    #

@app.route('/upload_all', methods=['GET', 'POST'])
def uoload_all():
    # 获取上传到这里的文件名，然后读取键值对，去上传文件，并返回结果
    # 一个开始尝试
    # 通过文件名获取到字典，赋值带着参数去post，post结果考虑，
    # 首先post失败的才能进行重新上传，
    # post结果有成功和不成功，不成功的话就告诉不成功
    # post成功需要把失败队列里面的内容删掉，然后加成功队列，键值对不用更改
    # 关于状态，和失败次数，post成功后需要重新记录失败次数，还是不用
    # 后台上传不修改任何参数，最多修改在那个队列
    datas = {
        "success":0,
        "fail":0
    }
    dic_json = request.get_json()
    print(dic_json)
    if dic_json:
        for video_id in dic_json["check_list"]:
            # print(video_id)
            dic = get_values(r, video_id)
            if dic:
                filename = dic["filename"]
                if os.path.exists(filename):
                    # fail_num = dic["fail_num"]
                    url = dic["url"]
                    formdata = {
                        "videoid": dic["data_id"],
                        "cameracode": dic["cameracode"],
                        "resultAddress": dic["resultAddress"],
                        "time_start": dic["time_start"]  # 需要校准
                    }
                    files = {'fileData': open(filename, 'rb')}
                    # try:
                    #     response = requests.post(url, data=formdata, files=files)
                    # except:
                    #     return jsonify({"error", "response error"})
                    response = requests.post(url, data=formdata, files=files)
                    if response.status_code == 200:
                        json_result = response.json()
                        # 这里的data_id 采用从redis中读取文件名，因为有可能返回的json文件无法获得文件名
                        if json_result['error_code'] == 0:
                            # 加入成功队列
                            remove_queue(r, "fail_queue", video_id)
                            write_queue(r, "finish_queue", video_id)
                            datas['success'] += 1
                        else:
                            datas['fail'] += 1

                    else:
                        # 服务器返回的状态码不对，比如404之类的
                        datas['fail'] += 1
                else:
                    datas['fail'] += 1

    return jsonify(datas)    #


@app.route('/update_fail_data', methods=['GET', 'POST'])
def update_fail_data():
    # 接收上传接口处理
    # 根据文件名读取键值对
    # 替换读取到的值
    # 写入到键值对中
    # 返回结果
    dic = request.get_json()
    if dic:
        video_id = dic['data_id']
        set_values(r,video_id,dic)
        return jsonify(True)

    return jsonify(False)



@app.route('/update_all', methods=['GET', 'POST'])
def update_all():
    dic_json = request.get_json()
    print(dic_json)
    if dic_json:
        for dic in dic_json['check_list']:
            print(dic)
            data_id = dic["data_id"]
            set_values(r,data_id,dic)
        return jsonify(True)

    return jsonify(False)


@app.route('/config_file', methods=['GET', 'POST'])
def config_file():
    # 读取配置文件，并可以修改配置
    # 读取配置文件，返回数据，分两种情况，
    # 一种是get，即读取文件进行显示，
    # 一种是post，需要修改参数的
    if platform.system() == 'Windows':
        filename = os.path.join('D:', '\\Code', 'test','linux', 'config.json')
    elif platform.system() == 'Linux':
        filename = os.path.join('/','opt','config.json')
    if request.method == "GET":
        # 读取json数据，并返回
        dic = read_jsonfile(filename)

    elif request.method == "POST":
        # 读取表格提交的数据，并写入
        dic_post = request.get_json()
        print(dic_post)
        # return dic_post
        if dic_post:
            dic_old = read_jsonfile(filename)
            if dic_old:
                dic_old['cut_time'] = dic_post['cut_time']
                dic_old['times'] = dic_post['times']
                dic_old['expire'] = dic_post['expire']
                dic_old['timing'] = dic_post['timing']
                dic_old['flag'] = dic_post['flag']
                for i in range(len(dic_old['rtsp_list'])):
                    dic_old['rtsp_list'][i]['rtsp_main_url'] = dic_post['rtsp_list'][i]['rtsp_main_url']
                    dic_old['rtsp_list'][i]['url'] = dic_post['rtsp_list'][i]['url']
                    dic_old['rtsp_list'][i]['resultAddress'] = dic_post['rtsp_list'][i]['resultAddress']
            else:
                return  False
        else:
            return False

        dic = dic_old
        # 写入data文件
        # if os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write(json.dumps(dic,indent=2)) # 书写的json格式会自己排版
            # json.dump(dic, f)
        # 写入配置文件成功时，应该删除当前的状态队列，删除整个键
        # 同时删除对应的键值对

        # rtsp_list = read_all_queue(r,"status_set",-1)
        # # print("rtsp_list:",rtsp_list)
        #
        # if rtsp_list:
        #     for rtmp in rtsp_list:
        #         # print("rtmp:",rtmp)
        #         remove_key(r,rtmp)
        # r.delete("status_set")
    # print(os.getcwd()) # 打印当前路径 D:\MyProgram\PyCharm 2020.1.3\jbr\bin
    return jsonify(dic)




if __name__ == '__main__':
    r = init_redis()
    if platform.system() == 'Windows':
        app.run(debug=True, host='127.0.0.1',port=5000)

    elif platform.system() == 'Linux':
        app.run(debug = True,host = '0.0.0.0',port=8003)


