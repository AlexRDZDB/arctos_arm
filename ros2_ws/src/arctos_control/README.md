# arctos_control

Pose tracking for the Arctos arm ("carrot on a stick"): the arm chases a target
pose published on a topic.

- **Far from the target** (more than 25 cm): plan and execute with MoveIt.
- **Close to the target**: MoveIt Servo tracks it continuously.

Only one of the two commands the arm at a time.

## Demo

The arm follows a figure eight (infinity symbol) in the XY plane, in Gazebo:

```bash
ros2 launch arctos_control carrot_demo.launch.py
```

| Argument | Default | Meaning |
|---|---|---|
| `gz_args` | `-r empty.sdf` | arguments for `gz sim` (world, `-r` to run, `-s` for headless) |
| `rviz` | `true` | start RViz with the MotionPlanning panel |

The launch file includes `arctos_simulation`'s `gazebo_moveit.launch.py` and
adds `servo_node`, the controller and the figure-eight publisher.

What to expect: the arm starts at home, about 30 cm from the target. It plans
towards it, switches to Servo once within 25 cm, then follows the figure eight
with a lag of roughly 5 to 10 mm. The figure is 0.20 m wide, centred at
(0, 0, 1.0) in `world` with the gripper pointing down, one lap about every
22 s.

To drive the controller with your own target, publish
`geometry_msgs/msg/PoseStamped` on `/desired_pose` instead of running
`figure_eight_publisher`.

## Nodes

### `carrot_on_a_stick_controller`

Decides between planning and servoing, and feeds the target to whichever is
active.

| | Name | Type | Notes |
|---|---|---|---|
| Subscribes | `/desired_pose` | `geometry_msgs/msg/PoseStamped` | the target (carrot). Poses in another frame are transformed to `planning_frame` |
| Subscribes | `/tf`, `/tf_static` | | current end effector pose |
| Publishes | `/servo_node/pose_target_cmds` | `geometry_msgs/msg/PoseStamped` | target for Servo, at `control_rate`, only in servo mode |
| Action client | `/move_action` | `moveit_msgs/action/MoveGroup` | plan and execute |
| Service client | `/servo_node/switch_command_type` | `moveit_msgs/srv/ServoCommandType` | puts Servo in pose mode at start-up |
| Service client | `/servo_node/pause_servo` | `std_srvs/srv/SetBool` | pauses Servo while the planner has the arm |

Behaviour:

1. Distance is the straight-line distance between the end effector
   (`ee_link`) and the target position.
2. Above `servo_distance` it sends a plan-and-execute goal to MoveIt.
3. While a plan runs, it is cancelled and redone if the target moves more than
   `replan_distance` from the pose the plan was heading to.
4. A running plan is also cancelled as soon as the arm is within
   `servo_distance`, and Servo takes over.
5. Servo hands back to the planner when the distance exceeds
   `servo_distance + hysteresis`.

| Parameter | Default | Meaning |
|---|---|---|
| `servo_distance` | `0.25` | [m] switch-over distance between planning and servoing |
| `hysteresis` | `0.02` | [m] extra distance before Servo gives the arm back to the planner |
| `replan_distance` | `0.05` | [m] target movement that triggers a new plan |
| `planning_frame` | `world` | frame the distances and goals are expressed in |
| `ee_link` | `Link_6_1` | end effector link |
| `group` | `arctos_arm` | MoveIt planning group |
| `velocity_scaling` | `0.3` | fraction of the joint velocity limits used by plans |
| `acceleration_scaling` | `0.3` | fraction of the joint acceleration limits used by plans |
| `planning_time` | `2.0` | [s] allowed planning time |
| `position_tolerance` | `0.01` | [m] goal tolerance of a plan |
| `orientation_tolerance` | `0.05` | [rad] goal tolerance of a plan |
| `retry_period` | `1.0` | [s] wait after a failed plan |
| `control_rate` | `50.0` | [Hz] update rate |
| `servo_node` | `servo_node` | name of the MoveIt Servo node |

### `figure_eight_publisher`

Test target: a pose tracing a figure eight in the XY plane of `frame`, at
constant height and orientation.

| | Name | Type | Notes |
|---|---|---|---|
| Publishes | `/desired_pose` | `geometry_msgs/msg/PoseStamped` | at `rate` |

| Parameter | Default | Meaning |
|---|---|---|
| `frame` | `world` | frame of the published pose |
| `center` | `[0.0, 0.0, 1.0]` | [m] centre of the figure (the demo launch sets it too) |
| `orientation` | `[0, 0, 0, 1]` | quaternion `[x, y, z, w]` held along the path (the demo launch sets gripper-down) |
| `half_width` | `0.10` | [m] half the length along X; each lobe is half of that in Y |
| `max_speed` | `0.04` | [m/s] highest target speed, reached at the crossing; the lap time follows from it |
| `rate` | `20.0` | [Hz] publish rate |

Keep `max_speed` below Servo's linear speed cap (`scale.linear` in
`config/servo.yaml`, 0.15 m/s) or the arm cannot keep up.

### `servo_node` (from `moveit_servo`)

Started by the demo launch with `config/servo.yaml`.

| | Name | Type |
|---|---|---|
| Subscribes | `/servo_node/pose_target_cmds` | `geometry_msgs/msg/PoseStamped` |
| Subscribes | `/joint_states`, `/monitored_planning_scene` | |
| Publishes | `/arctos_arm_controller/joint_trajectory` | `trajectory_msgs/msg/JointTrajectory` |
| Publishes | `/servo_node/status` | `moveit_msgs/msg/ServoStatus` |

## Servo settings

`config/servo.yaml` differs from the MoveIt Servo defaults in two places, both
specific to this arm:

- **Singularity thresholds are 30 / 60** (defaults 17 / 30). The arm is small,
  so its Jacobian condition number is 12 to 15 even in comfortable poses.
- **Self-collision margin is 0.5 mm** (default 1 cm). `Link_4_1` and
  `Gripper_1` are always about 0.8 mm apart and that pair is not disabled in
  the SRDF, so a larger margin makes Servo crawl. The table is part of the
  robot model, so this is also Servo's margin to the table.

## Known limitations

- **Targets close to the home pose stall.** Home (all joints at 0) is a wrist
  singularity. If the target is within `servo_distance` of the arm while it is
  at home, Servo takes over, cannot move, and nothing recovers it. Start from a
  pose with `joint5` bent, or with the target further away.
- **Servo does not plan around obstacles.** It slows down and stops near a
  collision; only the plan-and-execute phase finds a path around things.
- **Tested in simulation only**, not on the real arm.

## Build

`ament_python` package; needs `arctos_simulation` for the demo launch and
`ros-jazzy-moveit-servo` (in the Dockerfile):

```bash
colcon build --packages-up-to arctos_control
```
