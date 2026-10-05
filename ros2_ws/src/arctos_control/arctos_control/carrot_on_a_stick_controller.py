"""
Chases a pose target (the carrot) with the arm.

Far from the target the arm plans and executes with MoveIt; once the end
effector is within servo_distance it hands over to MoveIt Servo, which tracks
the target continuously. Only one of the two commands the arm at a time.
"""
import math
from enum import Enum

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    BoundingVolume,
    Constraints,
    MoveItErrorCodes,
    OrientationConstraint,
    PositionConstraint,
)
from moveit_msgs.srv import ServoCommandType
import rclpy
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from shape_msgs.msg import SolidPrimitive
from std_srvs.srv import SetBool
import tf2_geometry_msgs  # noqa: F401  registers PoseStamped with tf2
from tf2_ros import Buffer, TransformException, TransformListener


class Mode(Enum):
    IDLE = 'idle'
    PLAN = 'plan and execute'
    SERVO = 'servo'


def distance(a, b):
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


class CarrotOnAStickController(Node):

    def __init__(self):
        super().__init__('carrot_on_a_stick_controller')

        self.planning_frame = self.declare_parameter('planning_frame', 'world').value
        self.ee_link = self.declare_parameter('ee_link', 'Link_6_1').value
        self.group = self.declare_parameter('group', 'arctos_arm').value
        # Further than this from the target: plan and execute. Closer: servo
        self.servo_distance = self.declare_parameter('servo_distance', 0.25).value
        # Extra distance before servo gives the arm back to the planner, so a
        # target sitting right at servo_distance does not flip modes every cycle
        self.hysteresis = self.declare_parameter('hysteresis', 0.02).value
        # A plan in progress is redone once the target has moved this far from its goal
        self.replan_distance = self.declare_parameter('replan_distance', 0.05).value
        self.velocity_scaling = self.declare_parameter('velocity_scaling', 0.3).value
        self.acceleration_scaling = self.declare_parameter('acceleration_scaling', 0.3).value
        self.planning_time = self.declare_parameter('planning_time', 2.0).value
        self.position_tolerance = self.declare_parameter('position_tolerance', 0.01).value
        self.orientation_tolerance = self.declare_parameter('orientation_tolerance', 0.05).value
        self.retry_period = self.declare_parameter('retry_period', 1.0).value
        control_rate = self.declare_parameter('control_rate', 50.0).value
        servo_node = self.declare_parameter('servo_node', 'servo_node').value

        self.target = None  # latest target pose, in the planning frame
        self.mode = Mode.IDLE
        self.servo_ready = False
        self.busy = False  # waiting on a servo service or on a goal to be accepted
        self.goal_handle = None
        self.plan_goal = None  # pose the current plan is heading to
        self.cancelling = False
        self.next_plan_time = Time(clock_type=self.get_clock().clock_type)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.move_group = ActionClient(self, MoveGroup, 'move_action')
        self.switch_command_type = self.create_client(
            ServoCommandType, f'{servo_node}/switch_command_type')
        self.pause_servo = self.create_client(SetBool, f'{servo_node}/pause_servo')
        self.carrot_pub = self.create_publisher(
            PoseStamped, f'{servo_node}/pose_target_cmds', 10)

        self.create_subscription(PoseStamped, 'desired_pose', self.on_target, 10)
        self.create_timer(1.0 / control_rate, self.update)

    def on_target(self, msg):
        if msg.header.frame_id not in ('', self.planning_frame):
            try:
                msg.header.stamp = Time().to_msg()  # latest available transform
                msg = self.tf_buffer.transform(msg, self.planning_frame)
            except TransformException as e:
                self.get_logger().warn(
                    f'Dropping target: {e}', throttle_duration_sec=2.0)
                return
        self.target = msg.pose

    def update(self):
        if not self.servo_ready:
            self.setup_servo()
            return
        if self.target is None or self.busy:
            return
        ee = self.ee_position()
        if ee is None:
            return
        to_target = distance(ee, self.target.position)

        if self.mode == Mode.SERVO:
            if to_target > self.servo_distance + self.hysteresis:
                self.leave_servo()
            else:
                self.publish_carrot()
        elif self.mode == Mode.PLAN:
            if self.cancelling:
                return
            if to_target < self.servo_distance:
                self.cancel_plan('close enough to servo')
            elif distance(self.plan_goal.position, self.target.position) > self.replan_distance:
                self.cancel_plan('target moved')
        elif to_target < self.servo_distance:
            self.enter_servo()
        elif self.get_clock().now() >= self.next_plan_time:
            self.start_plan()

    def ee_position(self):
        try:
            tf = self.tf_buffer.lookup_transform(self.planning_frame, self.ee_link, Time())
        except TransformException as e:
            self.get_logger().warn(
                f'No end effector pose yet: {e}', throttle_duration_sec=2.0)
            return None
        return tf.transform.translation

    def set_mode(self, mode):
        if mode != self.mode:
            self.get_logger().info(f'Mode: {self.mode.value} -> {mode.value}')
            self.mode = mode

    # Servo

    def setup_servo(self):
        """Put Servo in pose tracking mode and keep it paused until it is needed."""
        if self.busy:
            return
        if not (self.switch_command_type.service_is_ready()
                and self.pause_servo.service_is_ready()
                and self.move_group.server_is_ready()):
            self.get_logger().info(
                'Waiting for move_group and servo_node...', throttle_duration_sec=5.0)
            return
        self.busy = True
        request = ServoCommandType.Request(command_type=ServoCommandType.Request.POSE)
        self.switch_command_type.call_async(request).add_done_callback(
            lambda _: self.set_servo_paused(True, self.on_servo_ready))

    def on_servo_ready(self):
        self.servo_ready = True
        self.get_logger().info('Ready, waiting for a target on desired_pose')

    def set_servo_paused(self, paused, then=None):
        self.busy = True

        def done(_):
            self.busy = False
            if then is not None:
                then()

        self.pause_servo.call_async(SetBool.Request(data=paused)).add_done_callback(done)

    def enter_servo(self):
        self.set_mode(Mode.SERVO)
        self.set_servo_paused(False)

    def leave_servo(self):
        # Servo has to be quiet before the planner takes the arm back
        self.set_servo_paused(True, lambda: self.set_mode(Mode.IDLE))

    def publish_carrot(self):
        carrot = PoseStamped()
        carrot.header.frame_id = self.planning_frame
        carrot.header.stamp = self.get_clock().now().to_msg()
        carrot.pose = self.target
        self.carrot_pub.publish(carrot)

    # Plan and execute

    def start_plan(self):
        self.set_mode(Mode.PLAN)
        self.busy = True
        self.cancelling = False
        self.plan_goal = self.target
        self.move_group.send_goal_async(self.make_goal(self.plan_goal)).add_done_callback(
            self.on_goal_response)

    def make_goal(self, pose):
        region = SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[self.position_tolerance])
        position = PositionConstraint(link_name=self.ee_link, weight=1.0)
        position.header.frame_id = self.planning_frame
        position.constraint_region = BoundingVolume(primitives=[region], primitive_poses=[pose])

        orientation = OrientationConstraint(link_name=self.ee_link, weight=1.0)
        orientation.header.frame_id = self.planning_frame
        orientation.orientation = pose.orientation
        orientation.absolute_x_axis_tolerance = self.orientation_tolerance
        orientation.absolute_y_axis_tolerance = self.orientation_tolerance
        orientation.absolute_z_axis_tolerance = self.orientation_tolerance

        goal = MoveGroup.Goal()
        goal.request.group_name = self.group
        goal.request.num_planning_attempts = 1
        goal.request.allowed_planning_time = self.planning_time
        goal.request.max_velocity_scaling_factor = self.velocity_scaling
        goal.request.max_acceleration_scaling_factor = self.acceleration_scaling
        goal.request.start_state.is_diff = True
        goal.request.goal_constraints = [Constraints(
            position_constraints=[position], orientation_constraints=[orientation])]
        goal.planning_options.plan_only = False
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        return goal

    def on_goal_response(self, future):
        self.busy = False
        self.goal_handle = future.result()
        if not self.goal_handle.accepted:
            self.get_logger().warn('move_group rejected the goal')
            self.plan_finished(retry_later=True)
            return
        self.goal_handle.get_result_async().add_done_callback(self.on_plan_result)

    def cancel_plan(self, reason):
        self.get_logger().info(f'Stopping the current plan: {reason}')
        self.cancelling = True
        self.goal_handle.cancel_goal_async()

    def on_plan_result(self, future):
        result = future.result()
        failed = (result.status != GoalStatus.STATUS_SUCCEEDED
                  or result.result.error_code.val != MoveItErrorCodes.SUCCESS)
        if failed and not self.cancelling:
            self.get_logger().warn(
                f'Plan and execute failed (MoveIt error code {result.result.error_code.val})')
        self.plan_finished(retry_later=failed and not self.cancelling)

    def plan_finished(self, retry_later):
        """Go back to idle; the next update decides between servo and a new plan."""
        self.goal_handle = None
        self.cancelling = False
        if retry_later:
            self.next_plan_time = self.get_clock().now() + Duration(seconds=self.retry_period)
        self.set_mode(Mode.IDLE)


def main():
    rclpy.init()
    node = CarrotOnAStickController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
