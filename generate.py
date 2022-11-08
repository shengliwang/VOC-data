# -*- encoding: utf-8 -*-
import argparse
import re
import sys
import os
import json
import numpy as np

# json文件的公用部分
template_json = {
    "label": "3#217寝室检测",# 在html上显示为图表的description
    "dataYNum": 2,          # 纵轴 数据的数目
    "yUnit": "ppb or ppm*10",  # 纵轴 数据的单位(ppm*100显示)
    "descriptions": [       # 纵轴 数据的描述，两个数据分别为co2和tvoc
        "CO2",              # 图表上显示为数据的描述
        "TVOC"
    ],
    "childDirs": [],        # 默认不包含任何子目录
    "childDirsUnit": "",    # 默认子目录在html上显示的单位为空
    "dirUnit": "",          # 默认当前目录显示的在html上显示的单位
    "xUnit": ""             # 默认当前图表x轴的单位
}
## arg from command line
tvoc = 0
tvoc_unit = ''  # 单位，解析后应该是ppb

co2 = 0
co2_unit = ''   # 单位，解析后应该是ppm

time_year = 0
time_month = 0
time_day = 0
time_hour = 0
time_minute = 0

dir = ''


## 根据 全局变量 template_json 去格式化 json
def formate_json_using_template(json_data):
    global template_json
    for key in template_json.keys():
        json_data[key] = template_json[key]

def save_json_to_file(json_data:dict, fpath:str):
    fpath = os.path.relpath(fpath)
    print("saving to " + fpath)
    with open(fpath,'w')as fp:
        json.dump(json_data, fp, indent=4, ensure_ascii=False)


# 命令行参数解析，解析错误会直接抛出异常退出程序。
def myarg_parse(args):
    global tvoc, tvoc_unit, co2, co2_unit
    global time_year, time_month, time_day, time_hour, time_minute
    global dir
    lst = re.match('(\d+)(.*)', args.co2)
    co2 = int(lst.group(1)) / 10
    co2_unit = lst.group(2)

    lst = re.match('(\d+)(.*)', args.tvoc)
    tvoc = int(lst.group(1))
    tvoc_unit = lst.group(2)

    lst = re.match('(\d+)/(\d+)/(\d+)\((\d+):(\d+)\)', args.time)
    time_year = lst.group(1)
    time_month = lst.group(2)
    time_day = lst.group(3)
    time_hour = lst.group(4)
    time_minute = lst.group(5)

    dir = "%s/%s/%s/%s" % (args.dir, time_year, time_month, time_day)


## 传入的json数据在html能画成一个图，这里把其按照年月日格式化一下
## 调用示例 formate_json(data, "2019")       => 为 2019年的数据 格式化json
##         formate_json(data, "2019", "10") => 为 2019年10月的数据 格式化json
##         formate_json(data, "2019", "10", "05")
# 或者
#          formate_json(data)   => 为 所有的年分格式化json数据，
def formate_json(jdata:dict, year='', month='', day=''):
    # 先使用 模板 
    formate_json_using_template(jdata)
 
    date = ''
    # day 不为空，代表当前记录的一天的数据 
    if day != '':
        date = day + "日" + date
        jdata["dirUnit"] = "本日(%s号)"%(day)
        jdata["xUnit"] = "小时"
        jdata["childDirsUnit"] = ""
    

    if month != '':
        date = month + "月" + date
        if jdata["dirUnit"] == '':
            jdata["dirUnit"] = "本月(%s月)"%(month)
            jdata["xUnit"] = "日"
            jdata["childDirsUnit"] = "日"

    if year != '': 
        date = year + "年" + date
        if jdata["dirUnit"] == '':
            jdata["dirUnit"] = "本年(%s年)"%(year)
            jdata["xUnit"] = "月"
            jdata["childDirsUnit"] = "月"

    # 如果 year 都为空的话，那么month day 肯定都会为空
    if year == '':
        jdata["dirUnit"] = "历年"
        jdata["xUnit"] = "年"
        jdata["childDirsUnit"] = "年"

    jdata["label"] = jdata["label"] + " " + date
    



## 从dir目录下的config.json文件中 读取 平均值和 数据的数目
## 如果遇到任何错误，则返回(0, [0, 0])
## 返回数据的格式为 (dataNum, [mean1, mean2])
def load_mean_data_from_dir(dir:str):
    f = dir + "/config.json"
    f = os.path.relpath(f)
    json_data = ''
    if (not os.path.exists(f)):
        print("[W] not find config file " + f + ". when loading mean data")
        return (0, [0, 0])

    with open(f,'r',encoding='utf8')as fp:
        try:
            json_data = json.load(fp)
        except:
            print("[W] fomat error in " + f + ". when loading mean data")
            return (0, [0, 0])

    num = 0
    mean = [0, 0]
    
    try:
        num = json_data["dataNum"]
    except:
        return (0, [0, 0])
    
    try: 
        mean = json_data["mean"]
    except:
        return (0, [0, 0])

    return (num, mean)


## load json from file
## 如果遇到错误(文件不存在，或者格式错误) 则返回 空 json 对象，即 `{}`
def load_json_from_file(jpath: str):
    jpath = os.path.relpath(jpath)
    jdata = json.loads("{}")
    if (not os.path.exists(jpath)):
        print("[W] file " + jpath + " not exists. generate {}")
        return jdata
    else:
        with open(jpath,'r',encoding='utf8')as fp:
            try: 
                jdata = json.load(fp)
            except:
                print("[W] file " + jpath + " fomate error. generate {}")
                jdata = json.loads("{}")
    return jdata

## 根据 子文件夹 计算平均值
## 返回 subdirs 列表： 子目录的名称
##     num: 所有子目录中共有的数据点数
##     mean: 所有子目录的数据的平局值
def calculate_mean_on_subdirs(parentdir:str):
    num = 0
    mean = [0, 0]
    subdirs = []
    for dir in os.listdir(parentdir):
        subdir = parentdir+"/"+dir
        if os.path.isfile(subdir):
            continue
        (num1, mean1) = load_mean_data_from_dir(subdir)
        mean[0] = (mean[0]*num + mean1[0]*num1) / (num+ num1)
        mean[1] = (mean[1]*num + mean1[1]*num1) / (num + num1)
        num += num1
        subdirs.append(dir)
        
    subdirs.sort()
    return subdirs, num, mean


def genrate_data_on_subdirs(parentdir:str):
    subdirs = []
    for dir in os.listdir(parentdir):
        if os.path.isfile(parentdir+"/"+dir):
            continue
        subdirs.append(dir)

    # 是否应该先按时间排序？ todo
    subdirs.sort()
    dataX = []
    dataY = [[], []]
    for dir in subdirs:
        path = parentdir + "/" + dir
        num, mean = load_mean_data_from_dir(path)
        dataX.append(dir)
        dataY[0].append(mean[0])
        dataY[1].append(mean[1])
    
    return dataX, dataY


# 更新历年，年，月的 config.json 文件
# 更新日的config.json另外实现。
# 1. 先计算子目录的
def update_json(dir_path:str, year='', month=''):
    config_f = dir_path + "/config.json"
    config_f = os.path.relpath(config_f)

    jdata = load_json_from_file(config_f)

    formate_json(jdata, year=year, month=month)

    subdirs, num, mean = calculate_mean_on_subdirs(dir_path)
    jdata["childDirs"] = subdirs
    jdata["dataNum"] = num
    jdata["mean"] = mean

    dataX, dataY = genrate_data_on_subdirs(dir_path)
    jdata["dataX"] = dataX
    jdata["dataY"] = dataY
    
    save_json_to_file(jdata, config_f)

# 更新 json 中的 x轴 和 y轴的数据 
# 我们的y轴有两个数据，方便操作，我们直接写死。
# co2 和 tvoc 分别为 y轴上的两个数据
# hour和minute用于生成对应的x坐标
def update_json_day(
    json_data:dict, 
    co2:str, tvoc:str, hour:str, minute:str):

    # 检查 json对象里是否有 dataX, dataY
    try:
        x = json_data["dataX"]
    except:
        json_data["dataX"] = []

    try:
        y = json_data["dataY"]
    except:
        json_data["dataY"] = [[],[]]   

    x = json_data["dataX"]
    y = json_data["dataY"]

    # 添加x坐标
    x.append(int(hour) + round(int(minute)/60, 1))

    # 添加y坐标
    y[0].append(int(co2))
    y[1].append(int(tvoc))

    json_data["dataX"] = x
    json_data["dataY"] = y

    # 更新 坐标的数目和相应的均值
    json_data["dataNum"] = len(x)
    json_data["mean"] = [np.mean(y[0]), np.mean(y[1])]
        
## 传入命令参数格式：
# --co2 <data> --tvoc <data> --time <data>
# 如果没有传入参数，获取传入参数错误，则不更新数据，返回非0
# 例如: python update_data.py --co2 450ppm --tvoc 900ppb --time 2022/10/05(14:00)
if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', required=True, help='directory where data saved: eg. ./data')
    parser.add_argument('--co2', required=True, help='co2 value: eg. 450ppm')
    parser.add_argument('--tvoc', required=True, help='tvoc value: eg. 900ppb')
    parser.add_argument('--time', required=True, help='time eg. 2022/10/05(14:00)', default=100)
    
    args = parser.parse_args()
    try:
        myarg_parse(args)
    except:
        sys.exit(1)

    

    print("tovc: "+ str(tvoc))
    print("co2: "+ str(co2))
    print(time_year)
    print(time_month)
    print(time_day)
    print(time_hour)
    print(time_minute)
    print(dir)

    ## 创建文件路径，如果不存在的话
    os.makedirs(dir, exist_ok=True)

    ## 保存本次测量的数据到 json文件中，若不存在则创建。
    day_json_file = dir + "/config.json"
    jdata = load_json_from_file(day_json_file)

    formate_json(jdata, year=time_year, month=time_month, 
        day=time_day)

    update_json_day(jdata, tvoc=tvoc, co2=co2,
                 hour=time_hour, minute=time_minute)

    print(jdata)
    save_json_to_file(jdata, day_json_file)

    ## 向上更 本月的数据
    update_json(dir + "/../", year=time_year, month=time_month)

    ## 向上更新本年的数据 
    update_json(dir + "/../../", year=time_year)

    ## 向上更新历年数据
    update_json(dir + "/../../../")
