# arctos_sensors

Sensor drivers for the Arctos arm: camera publishers. Both nodes publish on
`/camera/image_raw`, so run one or the other.

| Camera | Node |
|---|---|
| GigE Vision, over Ethernet (the Daheng MER2-160-75GM-P) | `gige_camera_publisher` |
| USB webcam (V4L2) | `camera_publisher` |

View the stream with `ros2 run rqt_image_view rqt_image_view /camera/image_raw`.

## Nodes

### `gige_camera_publisher`

Receives the stream of a GigE Vision camera with
[Aravis](https://github.com/AravisProject/aravis), and publishes each frame.

```bash
ros2 run arctos_sensors gige_camera_publisher
```

The camera has no DHCP server to get an address from, so it picks a link-local
one (`169.254.x.x`). The host's Ethernet adapter has to be on the same range.
Once, on the host, with the name `nmcli connection show` gives the adapter:

```bash
nmcli connection modify "Wired connection 2" ipv4.method link-local
nmcli connection up "Wired connection 2"
```

The container uses the host's network, so nothing else is needed inside it.

| | Name | Type | Notes |
|---|---|---|---|
| Publishes | `/camera/image_raw` | `sensor_msgs/msg/Image` | sensor data QoS (best effort) |

| Parameter | Default | Meaning |
|---|---|---|
| `camera` | `''` | IP address or Aravis device id; empty takes the first camera found |
| `frame` | `camera_link` | `frame_id` of the published images |
| `pixel_format` | `''` | GenICam pixel format, e.g. `Mono8`; empty keeps the camera's setting |
| `rate` | `30.0` | [Hz] frame rate, `0` keeps the camera's setting |
| `exposure` | `0.0` | [us] exposure time, `0` keeps the camera's setting |

Pixel formats and the encoding they are published with:

| Pixel format | Encoding |
|---|---|
| `Mono8` | `mono8` |
| `Mono10`, `Mono12`, `Mono16` | `mono16` |
| `BayerRG8`, `BayerBG8`, `BayerGB8`, `BayerGR8` | `bayer_rggb8`, `bayer_bggr8`, `bayer_gbrg8`, `bayer_grbg8` |
| `RGB8`, `BGR8` | `rgb8`, `bgr8` |

The MER2-160-75GM-P is monochrome, 1440x1080, `Mono8` or `Mono12`, up to
75 fps.

### `camera_publisher`

Reads frames from a V4L2 camera with OpenCV and publishes them.

```bash
ros2 run arctos_sensors camera_publisher
```

The camera must be plugged in before the container starts, so that
`/dev/videoN` exists inside it.

| | Name | Type | Notes |
|---|---|---|---|
| Publishes | `/camera/image_raw` | `sensor_msgs/msg/Image` | `bgr8`, sensor data QoS (best effort) |

| Parameter | Default | Meaning |
|---|---|---|
| `device` | `0` | camera index; `N` opens `/dev/videoN` |
| `frame` | `camera_link` | `frame_id` of the published images |
| `width` | `0` | [px] requested width, `0` keeps the camera's default |
| `height` | `0` | [px] requested height, `0` keeps the camera's default |
| `rate` | `30.0` | [Hz] requested frame rate and publish rate |

The camera picks the closest mode it supports; the one in use is logged at
start-up.
