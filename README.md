# Thesis
Undergraduate thesis work. Generating a stereo event camera dataset for underwater applications.

## Event camera output

Prophesee metavision [viewer](https://docs.prophesee.ai/stable/samples/modules/stream/viewer.html#chapter-samples-stream-viewer). Allows for streaming and recording of camera data. Run with: 
`metavision_viewer`

Open source [metavision driver](https://github.com/ros-event-camera/metavision_driver). Currently installed on personal computer at `metavisoin_driver_ws`, more in depth information on their github page. This is more of a quickstart for me. Make sure to source ROS2 and the driver folder itself with: 

```
cd metavision_driver_ws
source install/setup.bash
```

The driver can then be run with:
```
ros2 launch metavision_driver driver_node.launch.py
```

The renderer can then be run with:
```
ros2 launch event_camera_renderer renderer.launch.py
```

Which can be viewed in RQT.



## Event camera calibration files

### Biases

Adjusting biases [link](https://docs.prophesee.ai/stable/hw/manuals/biases.html#chapter-biases). Includes information about the bais settings and what they do, as well as the limits for the EVK4-HD model. An example file for biases is `camera_settings.json`:

```
{
 "ll_biases_state": {
  "bias": [
   {
    "name": "bias_diff",
    "value": 0
   },
   {
    "name": "bias_diff_on",
    "value": 0
   },
   {
    "name": "bias_diff_off",
    "value": 0
   },
   {
    "name": "bias_fo",
    "value": 0
   },
   {
    "name": "bias_hpf",
    "value": 0
   },
   {
    "name": "bias_refr",
    "value": 0
   }
  ]
 }
}
```


## Event camera calibration 

Prophesee [focus adjustment](https://docs.prophesee.ai/stable/samples/modules/calibration/focus.html#chapter-samples-calibration-focus) and [calibration](https://docs.prophesee.ai/stable/samples/modules/calibration/calibration_pipeline.html#chapter-samples-calibration-calibration-pipeline) pages. Requires the Metavision SDK (don't currently have). 
