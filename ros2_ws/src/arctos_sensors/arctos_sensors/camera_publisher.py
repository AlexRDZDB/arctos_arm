"""
Reads frames from a USB camera with OpenCV and publishes them as
sensor_msgs/Image.
"""
import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class CameraPublisher(Node):

    def __init__(self):
        super().__init__('camera_publisher')

        # Index N opens /dev/videoN
        device = self.declare_parameter('device', 0).value
        self.frame = self.declare_parameter('frame', 'camera_link').value
        # Requests to the driver, which picks the closest mode it supports.
        # 0 keeps the camera's default
        width = self.declare_parameter('width', 0).value
        height = self.declare_parameter('height', 0).value
        rate = self.declare_parameter('rate', 30.0).value

        self.capture = cv2.VideoCapture(device, cv2.CAP_V4L2)
        if not self.capture.isOpened():
            raise RuntimeError(f'Could not open camera /dev/video{device}')
        if width > 0:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height > 0:
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.capture.set(cv2.CAP_PROP_FPS, rate)
        # Keep only the newest frame so a slow timer never publishes stale ones
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, 'camera/image_raw', qos_profile_sensor_data)
        self.create_timer(1.0 / rate, self.publish)
        self.get_logger().info(
            f'Camera /dev/video{device}: '
            f'{int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))}x'
            f'{int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))} at '
            f'{self.capture.get(cv2.CAP_PROP_FPS):.0f} fps')

    def publish(self):
        ok, image = self.capture.read()
        if not ok:
            self.get_logger().warn('No frame from the camera', throttle_duration_sec=5.0)
            return

        msg = self.bridge.cv2_to_imgmsg(image, encoding='bgr8')
        msg.header.frame_id = self.frame
        msg.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(msg)

    def destroy_node(self):
        self.capture.release()
        super().destroy_node()


def main():
    rclpy.init()
    node = None
    try:
        node = CameraPublisher()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()


if __name__ == '__main__':
    main()
