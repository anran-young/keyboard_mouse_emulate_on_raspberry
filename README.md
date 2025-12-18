[![Build Status](https://travis-ci.com/quangthanh010290/keyboard_mouse_emulate_on_raspberry.svg?branch=master)](https://travis-ci.com/quangthanh010290/keyboard_mouse_emulate_on_raspberry)

# 先把它跑起来

## 第 1 步：安装/初始化

```
 sudo ./setup.sh
```


## 第 2.1 步：添加你的主机 MAC 地址

打开 `./server/btk_server.py`：
- 如果你是 iPad/iPhone 作为主机：建议把 `TARGET_ADDRESS` 留空（iOS/iPadOS 可能会变化/随机化蓝牙地址，写死会导致再次配对/连接失败）。
- 如果你是固定地址的主机且确实需要：再把主机的 MAC 地址填到 `TARGET_ADDRESS`。

> 懒得写成脚本，所以需要你手动改。


## 第 2.2 步：启动服务端

```
sudo ./boot.sh
```
## 第 3.1 步：运行键盘客户端（使用物理键盘）

- 需要在树莓派上接入一个物理键盘

```
./keyboard/kb_client.py
```

## 第 3.2 步：运行键盘客户端（不需要物理键盘，通过 dbus 发送字符串）

- 不需要在树莓派上接入物理键盘

```
./keyboard/send_string.py "hello client, I'm a keyboard"
```

## 第 3.3 步：运行鼠标客户端（使用物理鼠标）

- 需要在树莓派上接入一个物理鼠标
```
./mouse/mouse_client.py
```

## 第 3.4 步：运行鼠标客户端（不需要物理鼠标，通过 dbus 发送鼠标数据）

- 不需要在树莓派上接入物理鼠标
```
./mouse/mouse_emulate.py 0 10 0 0
```

# 想了解我在后台做了什么
[Make Raspberry Pi3 as an emulator bluetooth keyboard](https://thanhle.me/make-raspberry-pi3-as-an-emulator-bluetooth-keyboard/)

## 键盘配置演示（旧版本）

 [![ScreenShot](https://i0.wp.com/thanhle.me/wp-content/uploads/2020/02/bluetooth_mouse_emulate_on_ra%CC%81pberry.jpg)](https://www.youtube.com/watch?v=fFpIvjS4AXs)

## 鼠标配置演示（进行中）
[Emulate Bluetooth mouse with Raspberry Pi](https://thanhle.me/emulate-bluetooth-mouse-with-raspberry-pi/)
[![ScreenShot](https://i0.wp.com/thanhle.me/wp-content/uploads/2020/08/bluetooth_mouse_emulation_on_raspberry.jpg)](https://www.youtube.com/watch?v=fFpIvjS4AXs)
