from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder

CONTROLLERS = ['joint_state_broadcaster', 'arctos_arm_controller', 'gripper_controller']


def generate_launch_description():
    sim_share = get_package_share_directory('arctos_simulation')

    # Everything from arctos_moveit_config, except the robot description: the
    # one here swaps the mock ros2_control hardware for the Gazebo one
    moveit_config = (
        MoveItConfigsBuilder('arctos_scene', package_name='arctos_moveit_config')
        .robot_description(file_path=f'{sim_share}/urdf/arctos_scene_gazebo.urdf.xacro')
        .to_moveit_configs()
    )
    use_sim_time = {'use_sim_time': True}

    gz_args_arg = DeclareLaunchArgument(
        'gz_args',
        default_value='-r empty.sdf',
        description='Arguments passed to gz sim (world file, -r to run, -s for headless)',
    )
    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        description='Start RViz with the MoveIt motion planning panel',
    )

    # Lets Gazebo resolve the package://arctos_description/... mesh URIs
    gz_resource_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        PathJoinSubstitution([FindPackageShare('arctos_description'), '..']),
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ),
        launch_arguments={'gz_args': LaunchConfiguration('gz_args')}.items(),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[moveit_config.robot_description, use_sim_time],
    )

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', '-name', 'arctos'],
        output='screen',
    )

    # Joint states come from joint_state_broadcaster, not from the bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/image/raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/image/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        output='screen',
    )

    # The controller_manager lives inside Gazebo and only exists once the
    # robot has been spawned
    controllers = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn,
            on_exit=[
                Node(
                    package='controller_manager',
                    executable='spawner',
                    arguments=CONTROLLERS,
                    output='screen',
                ),
            ],
        )
    )

    move_group = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        parameters=[
            moveit_config.to_dict(),
            use_sim_time,
            {
                'publish_robot_description_semantic': True,
                'publish_planning_scene': True,
                'publish_geometry_updates': True,
                'publish_state_updates': True,
                'publish_transforms_updates': True,
            },
        ],
        output='screen',
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', PathJoinSubstitution(
            [FindPackageShare('arctos_moveit_config'), 'config', 'moveit.rviz'])],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
            use_sim_time,
        ],
        condition=IfCondition(LaunchConfiguration('rviz')),
        output='screen',
    )

    return LaunchDescription([
        gz_args_arg,
        rviz_arg,
        gz_resource_path,
        gz_sim,
        robot_state_publisher,
        spawn,
        bridge,
        controllers,
        move_group,
        rviz,
    ])
