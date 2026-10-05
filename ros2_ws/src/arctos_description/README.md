# arctos_description

Robot description of the Arctos arm: URDF/xacro files, meshes, and a scene that
mounts the arm on a table with an AprilTag and an eye-in-hand camera. Also
provides launch files to view the model in RViz and to run it in Gazebo with
simple per-joint position controllers.

## Credits

The Arctos arm URDF files and meshes come from the Arctos Robotics ROS
repository: <https://github.com/Arctos-Robotics/ROS>.

They were updated by Alejandro Rodriguez del Bosque to work with our current
setup: Ubuntu 24.04 and ROS 2 Jazzy with Gazebo Harmonic. The table, AprilTag,
camera and scene files, and the ROS 2 launch files, were added here.

The `license` field in `package.xml` is still a placeholder. Check the license
of the upstream repository before redistributing the arm files.

## Robot model

| File | Contents |
|---|---|
| `urdf/arctos_urdf.xacro` | The arm: links, joints, meshes, inertias |
| `urdf/arctos_scene.urdf.xacro` | Top-level model: arm + table + AprilTag + camera + Gazebo plugins |
| `urdf/table.urdf.xacro` | `table` macro: four-legged table with a `<name>_surface` mounting frame |
| `urdf/apriltag.urdf.xacro` | `apriltag` macro: AprilTag 36h11 id 0 on a 0.2 m sheet |
| `urdf/camera.urdf.xacro` | `camera` macro: 640x480 camera with an optical frame |
| `urdf/arctos_gazebo.xacro` | Gazebo plugins: camera rendering, joint states, per-joint position controllers |
| `urdf/materials.xacro` | Colours |

Joints:

| Joint | Type | Moves |
|---|---|---|
| `joint1` ... `joint6` | continuous | the six arm axes |
| `jaw1`, `jaw2` | prismatic, 0 to 0.015 m | the two gripper jaws |

Main frames: `world` -> `table` -> `table_surface` -> `base_link` ->
`Link_1_1` ... `Link_6_1` -> `Gripper_1` -> `Left_jaw_1` / `Right_jaw_1`.
`camera_link` and `camera_optical_frame` hang from `Gripper_1`; `apriltag`
hangs from `base_link`.

With every joint at 0 the gripper points along -Y of `base_link`. That pose is
a wrist singularity (`joint4` and `joint6` are aligned), which matters for
Cartesian control.

## Launch files

### `display.launch.py`

Shows the model in RViz.

```bash
ros2 launch arctos_description display.launch.py
```

| Argument | Default | Meaning |
|---|---|---|
| `model` | `urdf/arctos_scene.urdf.xacro` | xacro/URDF file to load |
| `jsp` | `true` | start a joint state publisher (turn off when something else publishes `/joint_states`) |
| `gui` | `true` | use the joint state publisher sliders |
| `rvizconfig` | `rviz/display.rviz` | RViz config file |
| `use_sim_time` | `false` | use the `/clock` topic |

### `gazebo.launch.py`

Spawns the scene in Gazebo and opens RViz. Joints are driven by Gazebo's own
position controllers, without ros2_control or MoveIt.

```bash
ros2 launch arctos_description gazebo.launch.py
```

| Argument | Default | Meaning |
|---|---|---|
| `model` | `urdf/arctos_scene.urdf.xacro` | xacro/URDF file to load |
| `gz_args` | `-r empty.sdf` | arguments for `gz sim` (world, `-r` to run, `-s` for headless) |

Move a joint:

```bash
ros2 topic pub --once /arctos/joint1/cmd_pos std_msgs/msg/Float64 "{data: 0.5}"
```

## Nodes and topics

This package has no nodes of its own. The launch files start these:

| Node | Started by | Publishes | Subscribes |
|---|---|---|---|
| `robot_state_publisher` | both | `/robot_description`, `/tf`, `/tf_static` | `/joint_states` |
| `joint_state_publisher` / `joint_state_publisher_gui` | `display` (when `jsp` is true) | `/joint_states` | |
| `rviz2` | both | | `/tf`, `/robot_description` |
| `ros_gz_bridge` `parameter_bridge` | `gazebo` | `/clock`, `/joint_states`, `/image/raw`, `/image/camera_info` | `/arctos/<joint>/cmd_pos` |
| `ros_gz_sim` `create` | `gazebo` | (spawns the robot, then exits) | `/robot_description` |

Topics bridged from Gazebo:

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo -> ROS | simulation time |
| `/joint_states` | `sensor_msgs/msg/JointState` | Gazebo -> ROS | all eight joints |
| `/image/raw` | `sensor_msgs/msg/Image` | Gazebo -> ROS | 640x480, 30 Hz, frame `camera_optical_frame` |
| `/image/camera_info` | `sensor_msgs/msg/CameraInfo` | Gazebo -> ROS | |
| `/arctos/<joint>/cmd_pos` | `std_msgs/msg/Float64` | ROS -> Gazebo | target position, one topic per joint (`joint1`...`joint6`, `jaw1`, `jaw2`) |

## Legacy files

`launch/*.launch`, `launch/controller.yaml`, `launch/urdf.rviz`,
`urdf/arctos.urdf`, `urdf/arctos_urdf.gazebo` and `urdf/arctos_urdf.trans` are
ROS 1 / Gazebo Classic files. The ROS 2 launch files do not use them.

## Build

`ament_python` package:

```bash
colcon build --packages-select arctos_description
```
