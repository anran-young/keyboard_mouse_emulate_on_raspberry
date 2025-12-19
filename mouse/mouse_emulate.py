#!/usr/bin/python3

import os
import sys
import dbus
import dbus.service
import dbus.mainloop.glib


class MouseClient():
	def __init__(self):
		super().__init__()
		'''这里开始是蓝牙部分'''
		self.state = [0, 0, 0, 0]
		'''将按钮和移动数据打包成字节数组'''
			# byte0: button state
			# byte1: x movement
			# byte2: y movement
			# byte3: wheel movement
		self.bus = dbus.SystemBus()
		'''连接到btkbservice服务'''
		self.btkservice = self.bus.get_object(
			'org.thanhle.btkbservice', '/org/thanhle/btkbservice')
		'''获取接口'''
		self.iface = dbus.Interface(self.btkservice, 'org.thanhle.btkbservice')
		'''这里结束是蓝牙部分'''
	def send_current(self):
		try:
			self.iface.send_mouse(0, bytes(self.state))
			'''
			调用接口的send_mouse方法发送鼠标数据
			第一个参数是设备ID，这里假设为0
			第二个参数是字节数组，包含按钮和移动数据
			'''
		except OSError as err:
			error(err)

if __name__ == "__main__":

	if (len(sys.argv) < 5):
		print("Usage: mouse_emulate [button_num dx dy dz]")
		exit()
	client = MouseClient()
	client.state[0] = int(sys.argv[1])
	client.state[1] = int(sys.argv[2])
	client.state[2] = int(sys.argv[3])
	client.state[3] = int(sys.argv[4])
	print("state:", client.state)
	client.send_current()

