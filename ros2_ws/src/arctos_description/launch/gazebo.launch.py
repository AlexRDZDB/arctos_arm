from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

JOINTS = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6', 'jaw1', 'jaw2']


def generate_launch_description():
    pkg_share = FindPackageShare('arctos_description')

    model_arg = DeclareLaunchArgument(
        'model',
        default_value=PathJoinSubstitution([pkg_share, 'urdf', 'arctos_scene.urdf.xacro']),
        description='Path to the robot xacro/urdf file',
    )
    gz_args_arg = DeclareLaunchArgument(
        'gz_args',
        default_value='-r empty.sdf',
        description='Arguments passed to gz sim (world file, -r to run, -s for headless)',
    )

    # Lets Gazebo resolve the package://arctos_description/... mesh URIs
    gz_resource_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        PathJoinSubstitution([pkg_share, '..']),
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ),
        launch_arguments={'gz_args': LaunchConfiguration('gz_args')}.items(),
    )

    # robot_state_publisher + RViz, with joint states coming from Gazebo
    # instead of joint_state_publisher
    display = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_share, 'launch', 'display.launch.py'])
        ),
        launch_arguments={
            'model': LaunchConfiguration('model'),
            'jsp': 'false',
            'use_sim_time': 'true',
        }.items(),
    )

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', '-name', 'arctos'],
        output='screen',
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
            '/image/raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/image/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ] + [
            f'/arctos/{joint}/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double'
            for joint in JOINTS
        ],
        output='screen',
    )

    return LaunchDescription([
        model_arg,
        gz_args_arg,
        gz_resource_path,
        gz_sim,
        display,
        spawn,
        bridge,
    ])
