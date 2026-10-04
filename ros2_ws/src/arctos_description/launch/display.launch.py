from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import (
    AndSubstitution,
    Command,
    LaunchConfiguration,
    NotSubstitution,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_share = FindPackageShare('arctos_description')

    model_arg = DeclareLaunchArgument(
        'model',
        default_value=PathJoinSubstitution([pkg_share, 'urdf', 'arctos_scene.urdf.xacro']),
        description='Path to the robot xacro/urdf file',
    )
    jsp_arg = DeclareLaunchArgument(
        'jsp',
        default_value='true',
        description='Start a joint_state_publisher (disable when something else '
                    'publishes /joint_states, e.g. Gazebo)',
    )
    gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='true',
        description='Use the joint_state_publisher GUI sliders',
    )
    rvizconfig_arg = DeclareLaunchArgument(
        'rvizconfig',
        default_value=PathJoinSubstitution([pkg_share, 'rviz', 'display.rviz']),
        description='Path to the RViz config file',
    )
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use the simulation clock from /clock',
    )

    jsp = LaunchConfiguration('jsp')
    gui = LaunchConfiguration('gui')
    use_sim_time = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)

    robot_description = ParameterValue(
        Command(['xacro ', LaunchConfiguration('model')]),
        value_type=str,
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time,
        }],
    )
    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        condition=IfCondition(AndSubstitution(jsp, NotSubstitution(gui))),
    )
    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        condition=IfCondition(AndSubstitution(jsp, gui)),
    )
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', LaunchConfiguration('rvizconfig')],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    return LaunchDescription([
        model_arg,
        jsp_arg,
        gui_arg,
        rvizconfig_arg,
        use_sim_time_arg,
        robot_state_publisher,
        joint_state_publisher,
        joint_state_publisher_gui,
        rviz,
    ])
