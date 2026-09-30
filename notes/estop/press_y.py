#!/usr/bin/env python3
# One Xbox-Y press on /joy (neutral, Y, neutral), then exit.
import time, rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
rclpy.init(); n = Node("press_y_once"); p = n.create_publisher(Joy, "/joy", 10)
end = time.time() + 0.6
while time.time() < end: rclpy.spin_once(n, timeout_sec=0.05)
for b in (0, 1, 0):
    m = Joy(); m.header.frame_id = "joy"; m.header.stamp = n.get_clock().now().to_msg()
    m.axes = [0.0] * 8; m.buttons = [0] * 11; m.buttons[3] = b; p.publish(m)
    t = time.time(); print(time.strftime("%H:%M:%S", time.gmtime(t)) + ".%03d  /joy Y=%d" % (int(t % 1 * 1000), b), flush=True)
    s = time.time() + 0.2
    while time.time() < s: rclpy.spin_once(n, timeout_sec=0.05)
