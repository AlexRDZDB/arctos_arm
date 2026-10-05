"""
Test target for the carrot controller: a pose that traces a figure eight
(infinity symbol) in the XY plane of the planning frame at constant height
and orientation.
"""
import math

from geometry_msgs.msg import PoseStamped
import rclpy
from rclpy.node import Node


class FigureEightPublisher(Node):

    def __init__(self):
        super().__init__('figure_eight_publisher')

        self.frame = self.declare_parameter('frame', 'world').value
        self.center = self.declare_parameter('center', [0.0, 0.0, 1.0]).value
        # Orientation held along the whole path, as a quaternion [x, y, z, w]
        self.orientation = self.declare_parameter('orientation', [0.0, 0.0, 0.0, 1.0]).value
        # Half the length of the figure along X; each lobe is half_width / 2 tall in Y
        self.half_width = self.declare_parameter('half_width', 0.10).value
        # Fastest the target ever moves, reached at the crossing in the middle.
        # Keep it below what the arm can follow (Servo's linear speed cap)
        self.max_speed = self.declare_parameter('max_speed', 0.04).value
        rate = self.declare_parameter('rate', 20.0).value

        # x = a sin(wt), y = (a / 2) sin(2wt) peaks at a speed of sqrt(2) a w
        self.omega = self.max_speed / (math.sqrt(2.0) * self.half_width)
        self.start = None

        self.pub = self.create_publisher(PoseStamped, 'desired_pose', 10)
        self.create_timer(1.0 / rate, self.publish)
        self.get_logger().info(
            f'Figure eight {2 * self.half_width:.2f} m wide, one lap every '
            f'{2 * math.pi / self.omega:.1f} s, peak speed {self.max_speed:.3f} m/s')

    def publish(self):
        now = self.get_clock().now()
        if now.nanoseconds == 0:
            return  # simulation clock not received yet
        if self.start is None:
            self.start = now
        phase = self.omega * (now - self.start).nanoseconds * 1e-9

        msg = PoseStamped()
        msg.header.frame_id = self.frame
        msg.header.stamp = now.to_msg()
        msg.pose.position.x = self.center[0] + self.half_width * math.sin(phase)
        msg.pose.position.y = self.center[1] + self.half_width / 2 * math.sin(2 * phase)
        msg.pose.position.z = self.center[2]
        (msg.pose.orientation.x, msg.pose.orientation.y,
         msg.pose.orientation.z, msg.pose.orientation.w) = self.orientation
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = FigureEightPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
