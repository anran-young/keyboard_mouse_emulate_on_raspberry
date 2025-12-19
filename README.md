[![Build Status](https://travis-ci.com/quangthanh010290/keyboard_mouse_emulate_on_raspberry.svg?branch=master)](https://travis-ci.com/quangthanh010290/keyboard_mouse_emulate_on_raspberry)

# 先把项目跑起来

## 第一步：安装依赖

```
 sudo ./setup.sh
```


## 第二步（可选）：填写主机 MAC

打开 `./server/btk_server.py`，把你的主机（例如 iPad/电脑）的 MAC 地址填到 `TARGET_ADDRESS` 变量（原注释写在第 26 行附近）。

> 原作者懒得做成脚本参数，所以需要你手动改。


## 第三步：启动服务端

```
sudo ./boot.sh
```

### 配对（自动确认）

项目已在 `server/auto_pair_agent.py` 注册 BlueZ Agent，并在启动时设为 DefaultAgent：当 iPad 发起配对时会自动接受确认/授权，不再需要在树莓派端手动点击确认。

- Agent 日志：`/tmp/auto_pair_agent.log`

#### 如果 iPad 提示“配对不成功/忽略此设备”

通常是旧的 Bond/密钥残留导致，需要两边都清理后重新配对：

```bash
# 树莓派端：列出已配对设备并删除对应 iPad
sudo bluetoothctl paired-devices
sudo bluetoothctl remove <IPAD_MAC>

# 可选：重启蓝牙服务
sudo systemctl restart bluetooth.service
```

然后在 iPad 蓝牙列表里点“忽略此设备”，再重新搜索并配对。


## 第四步：运行键盘客户端（使用物理键盘）

- 需要树莓派接入一个物理键盘

```
./keyboard/kb_client.py
```

## 第五步：运行键盘客户端（无需物理键盘，通过 DBus 发送字符串）

- 不需要树莓派接入物理键盘

```
./keyboard/send_string.py "hello client, I'm a keyboard"
```

## 第六步：运行鼠标客户端（使用物理鼠标）

- 需要树莓派接入一个物理鼠标
```
./mouse/mouse_client.py
```

## 第七步：运行鼠标客户端（无需物理鼠标，通过 DBus 发送鼠标数据）

- 不需要树莓派接入物理鼠标
```
./mouse/mouse_emulate.py 0 10 0 0
```

# 原理说明（项目做了什么）
[将 Raspberry Pi3 模拟成蓝牙键盘](https://thanhle.me/make-raspberry-pi3-as-an-emulator-bluetooth-keyboard/)

## 键盘演示（旧版本）

 [![ScreenShot](https://i0.wp.com/thanhle.me/wp-content/uploads/2020/02/bluetooth_mouse_emulate_on_ra%CC%81pberry.jpg)](https://www.youtube.com/watch?v=fFpIvjS4AXs)

## 鼠标演示（持续更新）
[将 Raspberry Pi 模拟成蓝牙鼠标](https://thanhle.me/emulate-bluetooth-mouse-with-raspberry-pi/)
[![ScreenShot](https://i0.wp.com/thanhle.me/wp-content/uploads/2020/08/bluetooth_mouse_emulation_on_raspberry.jpg)](https://www.youtube.com/watch?v=fFpIvjS4AXs)
