# arctos_simulation

Gazebo simulation of the Arctos scene, driven through ros2_control so that
MoveIt (configured in `arctos_moveit_config`) can plan and execute motions on
the simulated arm.

It differs from `arctos_description`'s `gazebo.launch.py`, which moves the
joints with Gazebo's own position controllers and has no MoveIt connection.

## Launch

```bash
ros2 launch arctos_simulation gazebo_moveit.launch.py
```

| Argument | Default | Meaning |
|---|---|---|
| `gz_args` | `-r empty.sdf` | arguments for `gz sim` (world, `-r` to run, `-s` for headless) |
| `rviz` | `true` | start RViz with the MotionPlanning panel |

In RViz, drag the end effector marker, then press *Plan & Execute*: the arm
moves in Gazebo.

Headless:

```bash
ros2 launch arctos_simulation gazebo_moveit.launch.py \
    gz_args:="-r -s --headless-rendering empty.sdf" rviz:=false
```

## How it fits together

| File | Role |
|---|---|
| `urdf/arctos_scene_gazebo.urdf.xacro` | The scene (arm, table, AprilTag, camera), rebuilt from the `arctos_description` macros with ros2_control instead of `arctos_gazebo.xacro` |
| `urdf/arctos_gz_ros2_control.xacro` | ros2_control hardware (`gz_ros2_control/GazeboSimSystem`) and the Gazebo plugins |
| `launch/gazebo_moveit.launch.py` | Starts Gazebo, the controllers, `move_group` and RViz |

- The controllers are loaded from
  `arctos_moveit_config/config/ros2_controllers.yaml`; there is no second copy.
- MoveIt uses all of `arctos_moveit_config` except the robot description, which
  is the one from this package. Everything runs on simulation time.
- The scene layout is duplicated from
  `arctos_description/urdf/arctos_scene.urdf.xacro`. If the table, tag or camera
  placement changes there, change it here too. Link and joint names must keep
  matching the SRDF.

## Nodes and topics

This package has no nodes of its own. The launch file starts:

| Node | Publishes | Subscribes | Actions / services |
|---|---|---|---|
| `gz sim` with `gz_ros2_control` (hosts `controller_manager`) | | `/robot_description` | `/controller_manager/*` services |
| `joint_state_broadcaster` | `/joint_states`, `/dynamic_joint_states` | | |
| `arctos_arm_controller` | `/arctos_arm_controller/controller_state` | `/arctos_arm_controller/joint_trajectory` | action `/arctos_arm_controller/follow_joint_trajectory` |
| `gripper_controller` | | | action `/gripper_controller/gripper_cmd` |
| `robot_state_publisher` | `/robot_description`, `/tf`, `/tf_static` | `/joint_states` | |
| `ros_gz_bridge` `parameter_bridge` | `/clock`, `/image/raw`, `/image/camera_info` | | |
| `ros_gz_sim` `create` | (spawns the robot, then exits) | `/robot_description` | |
| `move_group` | `/monitored_planning_scene`, `/display_planned_path`, `/robot_description_semantic` | `/joint_states`, `/tf`, `/planning_scene` | action `/move_action`, `/execute_trajectory`; services `/compute_ik`, `/compute_fk` |
| `rviz2` (when `rviz` is true) | `/planning_scene` | `/monitored_planning_scene`, `/display_planned_path` | |

Camera: `/image/raw` is 640x480 at 30 Hz, stamped with frame
`camera_optical_frame`.

Check the controllers:

```bash
ros2 control list_controllers
```

All three should be `active`.

## Known limitations

- **`jaw2` does not move.** The gripper controller drives `jaw1` only (see
  `arctos_moveit_config`), so the simulated gripper closes on one side.

## Build

`ament_cmake` package; needs `arctos_description` and `arctos_moveit_config`:

```bash
colcon build --packages-up-to arctos_simulation
```
