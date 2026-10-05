# arctos_moveit_config

MoveIt 2 configuration for the Arctos scene (`arctos_scene`), generated with
the MoveIt Setup Assistant from
`arctos_description/urdf/arctos_scene.urdf.xacro`. Other packages load their
planning groups, kinematics, limits and controller definitions from here.

To change it, rerun the assistant:

```bash
ros2 launch arctos_moveit_config setup_assistant.launch.py
```

## Configuration

| File | Contents |
|---|---|
| `config/arctos_scene.srdf` | planning groups, named poses, end effector, disabled collision pairs |
| `config/kinematics.yaml` | IK solver for `arctos_arm` (KDL) |
| `config/joint_limits.yaml` | velocity and acceleration limits; default scaling of 0.1 |
| `config/moveit_controllers.yaml` | which controllers MoveIt sends trajectories to |
| `config/ros2_controllers.yaml` | ros2_control controllers (also used by `arctos_simulation`) |
| `config/arctos_scene.urdf.xacro`, `config/arctos_scene.ros2_control.xacro` | robot model with mock ros2_control hardware |
| `config/initial_positions.yaml` | start pose of the mock hardware |
| `config/pilz_cartesian_limits.yaml` | Cartesian limits for the Pilz planner |
| `config/moveit.rviz` | RViz layout with the MotionPlanning panel |

Planning groups:

| Group | Joints | Named poses |
|---|---|---|
| `arctos_arm` | `joint1` ... `joint6` | `home` (all 0) |
| `gripper` | `jaw1`, `jaw2` | `gripper_open` (0), `gripper_close` (0.015) |

The end effector link of `arctos_arm` is `Link_6_1`.

Controllers:

| Controller | Type | Joints | Action |
|---|---|---|---|
| `arctos_arm_controller` | `JointTrajectoryController` | `joint1` ... `joint6` | `/arctos_arm_controller/follow_joint_trajectory` |
| `gripper_controller` | `GripperActionController` | `jaw1` | `/gripper_controller/gripper_cmd` |
| `joint_state_broadcaster` | `JointStateBroadcaster` | all | |

## Launch files

| Launch file | Starts |
|---|---|
| `demo.launch.py` | everything below, with mock hardware: the quickest way to try MoveIt without Gazebo |
| `move_group.launch.py` | the `move_group` node |
| `moveit_rviz.launch.py` | RViz with the MotionPlanning panel |
| `rsp.launch.py` | `robot_state_publisher` |
| `spawn_controllers.launch.py` | the three controllers |
| `static_virtual_joint_tfs.launch.py` | static transforms for virtual joints (none defined) |
| `warehouse_db.launch.py` | MoveIt warehouse database |
| `setup_assistant.launch.py` | MoveIt Setup Assistant |

```bash
ros2 launch arctos_moveit_config demo.launch.py
```

To run MoveIt against Gazebo instead, use `arctos_simulation`.

## Nodes and topics

This package has no nodes of its own. `demo.launch.py` starts:

| Node | Publishes | Subscribes | Actions / services |
|---|---|---|---|
| `move_group` | `/monitored_planning_scene`, `/display_planned_path`, `/robot_description_semantic` | `/joint_states`, `/tf`, `/planning_scene` | action `/move_action`, `/execute_trajectory`; services `/compute_ik`, `/compute_fk`, `/plan_kinematic_path`, `/get_planning_scene` |
| `ros2_control_node` (mock hardware) | | | hosts the controllers |
| `joint_state_broadcaster` | `/joint_states`, `/dynamic_joint_states` | | |
| `arctos_arm_controller` | `/arctos_arm_controller/controller_state` | `/arctos_arm_controller/joint_trajectory` | action `/arctos_arm_controller/follow_joint_trajectory` |
| `gripper_controller` | | | action `/gripper_controller/gripper_cmd` |
| `robot_state_publisher` | `/robot_description`, `/tf`, `/tf_static` | `/joint_states` | |
| `rviz2` | `/planning_scene` (from the MotionPlanning panel) | `/monitored_planning_scene`, `/display_planned_path` | |

## Known limitations

- **Only `jaw1` is driven.** `gripper_controller` commands `jaw1`, and `jaw2`
  has no controller or `<mimic>` tag, so the gripper closes on one side only.
- **Close link pairs are still collision-checked.** `Link_4_1`-`Gripper_1`
  (about 0.8 mm apart) and `Link_4_1`-`Link_6_1` (about 2.6 mm) are not
  disabled in the SRDF. Planning works, but MoveIt Servo treats them as a near
  collision; `arctos_control` works around it in its Servo settings.

## Build

`ament_cmake` package:

```bash
colcon build --packages-select arctos_moveit_config
```
