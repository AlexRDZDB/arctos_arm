"""
Receives the stream of a GigE Vision camera (Ethernet) with Aravis, decodes
each frame and publishes it as sensor_msgs/Image.
"""
from array import array

import gi
gi.require_version('Aravis', '0.8')
from gi.repository import Aravis  # noqa: E402
import rclpy  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import qos_profile_sensor_data  # noqa: E402
from sensor_msgs.msg import Image  # noqa: E402

# GenICam pixel format -> (ROS image encoding, bytes per pixel). The camera
# sends 10 and 12 bit pixels in 16 bit words, with the upper bits at zero
ENCODINGS = {
    'Mono8': ('mono8', 1),
    'Mono10': ('mono16', 2),
    'Mono12': ('mono16', 2),
    'Mono16': ('mono16', 2),
    'BayerRG8': ('bayer_rggb8', 1),
    'BayerBG8': ('bayer_bggr8', 1),
    'BayerGB8': ('bayer_gbrg8', 1),
    'BayerGR8': ('bayer_grbg8', 1),
    'RGB8': ('rgb8', 3),
    'BGR8': ('bgr8', 3),
}


class GigeCameraPublisher(Node):

    def __init__(self):
        super().__init__('gige_camera_publisher')

        # IP address or Aravis device id; empty takes the first camera found
        camera = self.declare_parameter('camera', '').value
        self.frame = self.declare_parameter('frame', 'camera_link').value
        # Empty keeps the format the camera is set to
        pixel_format = self.declare_parameter('pixel_format', '').value
        # [Hz] 0 keeps the camera's setting
        rate = self.declare_parameter('rate', 30.0).value
        # [us] 0 keeps the camera's setting
        exposure = self.declare_parameter('exposure', 0.0).value

        self.camera = Aravis.Camera.new(camera or None)
        if pixel_format:
            self.camera.set_pixel_format_from_string(pixel_format)
        if rate > 0.0:
            # Daheng cameras ignore the frame rate until this switch is on
            device = self.camera.get_device()
            if device.get_feature('AcquisitionFrameRateMode') is not None:
                device.set_string_feature_value('AcquisitionFrameRateMode', 'On')
            self.camera.set_frame_rate(rate)
        if exposure > 0.0:
            self.camera.set_exposure_time(exposure)

        pixel_format = self.camera.get_pixel_format_as_string()
        if pixel_format not in ENCODINGS:
            raise RuntimeError(f'Pixel format {pixel_format} is not supported')
        self.encoding, self.bytes_per_pixel = ENCODINGS[pixel_format]

        # Largest packets the link carries without fragmenting them
        self.camera.gv_auto_packet_size()
        self.stream = self.camera.create_stream(None, None)
        payload = self.camera.get_payload()
        for _ in range(10):
            self.stream.push_buffer(Aravis.Buffer.new_allocate(payload))

        self.pub = self.create_publisher(Image, 'camera/image_raw', qos_profile_sensor_data)
        self.camera.start_acquisition()
        self.last_frame = self.get_clock().now()
        # Poll twice per frame so a frame never waits long in the stream
        self.create_timer(0.5 / self.camera.get_frame_rate(), self.receive)

        region = self.camera.get_region()
        self.get_logger().info(
            f'{self.camera.get_vendor_name()} {self.camera.get_model_name()}: '
            f'{region.width}x{region.height} {pixel_format} at '
            f'{self.camera.get_frame_rate():.0f} fps')

    def receive(self):
        while True:
            buffer = self.stream.try_pop_buffer()
            if buffer is None:
                break
            self.last_frame = self.get_clock().now()
            if buffer.get_status() == Aravis.BufferStatus.SUCCESS:
                self.publish(buffer)
            else:
                # Packets of this frame were lost on the way
                self.get_logger().warn(
                    f'Dropped a frame: {buffer.get_status().value_nick}',
                    throttle_duration_sec=5.0)
            self.stream.push_buffer(buffer)

        if (self.get_clock().now() - self.last_frame).nanoseconds > 1e9:
            self.get_logger().warn('No frame from the camera', throttle_duration_sec=5.0)

    def publish(self, buffer):
        msg = Image()
        msg.header.frame_id = self.frame
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.width = buffer.get_image_width()
        msg.height = buffer.get_image_height()
        msg.encoding = self.encoding
        msg.is_bigendian = 0
        msg.step = msg.width * self.bytes_per_pixel
        # As an array, or rclpy checks the type of every byte, at about 5 fps
        msg.data = array('B', buffer.get_data())
        self.pub.publish(msg)

    def destroy_node(self):
        self.camera.stop_acquisition()
        super().destroy_node()


def main():
    rclpy.init()
    node = None
    try:
        node = GigeCameraPublisher()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()


if __name__ == '__main__':
    main()
