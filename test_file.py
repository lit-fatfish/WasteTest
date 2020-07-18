import os
from datetime import date
import datetime
import  shutil



def get_days_list(num):
    list_days = []
    today = date.today()
    for i in range(num):
        day = datetime.timedelta(i)
        list_days.append(str(today-day))
    return list_days


print(get_days_list(7))

def clear_file(path,num):
    list_days = get_days_list(num)
    list = os.listdir(path)
    for filename in list:
        if filename not in list_days:
            # 文件名不在列表中
            if os.path.isdir(filename):
                # 删除文件夹
                shutil.rmtree(filename)
            elif os.path.isfile(filename):
                # 删除文件
                os.remove(filename)





