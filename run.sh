#!/bin/bash

### note
# 本脚本暂时没有实现一些错误判断。待优化 

pushd /home/hou/vicking/VOC-data

# 检查 ko 是否加载 
lsmod | grep sensor &> /dev/null
if [ $? != 0 ]
then
    echo "sensor.ko not load"
    echo "insmod sensor.ko"
    pushd driver
    ./insmod.sh
    popd
    sudo driver/sgp30 -i  # 初始化 sgp30 传感器
else
    echo "sensor.ko is load"
fi

# 生成数据
TIME=`date +'%Y/%m/%d(%H:%M)'`
echo "current time is $TIME"
DATA=`sudo driver/sgp30 -m | grep "[0-9]\+pp" -o | grep "[0-9]\+" -o`
echo $DATA
CO2=`echo $DATA | cut -d ' ' -f1`
TVOC=`echo $DATA | cut -d ' ' -f2`
echo "co2 is $CO2 TVOC is $TVOC"

CMDLINE="--tvoc ${TVOC}ppb --co2 ${CO2}ppm --time ${TIME} --dir ./data"
echo $CMDLINE

python3 generate.py $CMDLINE



## 更新数据到github上
git status | grep "data"

if [ $? != 0 ]
then 
    echo "nothing to commit"
    exit
fi

git add data/
git commit -m "python3 generate.py $CMDLINE"
git push origin main
