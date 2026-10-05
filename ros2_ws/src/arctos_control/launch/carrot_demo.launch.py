from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder
import yaml

# Figure eight over the table in front of the arm, gripper pointing straight
# down. Every pose on it is reachable with joint5 well away from the wrist
# singularity at 0
FIGURE_EIGHT_CENTER = [0.0, 0.0, 1.0]
GRIPPER_DOWN = [0.7071068, 0.0, 0.0, 0.7071068]


def generate_launch_description():
    sim_share = get_package_share_directory('arctos_simulation')
    control_share = get_package_share_directory('arctos_control')

    # Same robot model the simulation launch gives move_group
    moveit_config = (
        MoveItConfigsBuilder('arctos_scene', package_name='arctos_moveit_config')
        .robot_description(file_path=f'{sim_share}/urdf/arctos_scene_gazebo.urdf.xacro')
        .to_moveit_configs()
    )
    with open(f'{control_share}/config/servo.yaml') as f:
        servo_params = {'moveit_servo': yaml.safe_load(f)}
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

    # Gazebo, controllers, move_group and RViz
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare('arctos_simulation'), 'launch', 'gazebo_moveit.launch.py'])
        ),
        launch_arguments={
            'gz_args': LaunchConfiguration('gz_args'),
            'rviz': LaunchConfiguration('rviz'),
        }.items(),
    )

    servo = Node(
        package='moveit_servo',
        executable='servo_node',
        name='servo_node',
        parameters=[
            servo_params,
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            use_sim_time,
        ],
        output='screen',
    )

    controller = Node(
        package='arctos_control',
        executable='carrot_on_a_stick_controller',
        parameters=[use_sim_time],
        output='screen',
    )

    figure_eight = Node(
        package='arctos_control',
        executable='figure_eight_publisher',
        parameters=[
            use_sim_time,
            {
                'center': FIGURE_EIGHT_CENTER,
                'orientation': GRIPPER_DOWN,
                'half_width': 0.10,
                'max_speed': 0.04,
            },
        ],
        output='screen',
    )

    return LaunchDescription([
        gz_args_arg,
        rviz_arg,
        simulation,
        servo,
        controller,
        figure_eight,
    ])
