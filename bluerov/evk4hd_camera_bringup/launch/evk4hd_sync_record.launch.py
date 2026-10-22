#!/usr/bin/env python3
"""
evk4hd_sync_record.launch.py

Adapted from metavision_driver's stereo_driver.launch.py, with a
rosbag2_composable_recorder added to the same container for
synchronized, intra-process bag recording.

Example usage of script: 

ros2 launch evk4hd_camera_bringup evk4hd_sync_record.launch.py \
primary_serial:=00052135 \
secondary_serial:=00052136 \
bag_prefix:=/home/ryan/unsw/thesis/ros_recordings/sync \
bias_file:=/home/ryan/unsw/thesis/camera_files/checkerboard_detection_3.bias

To start recording:

ros2 service call /start_recording std_srvs/srv/Trigger

To stop:

ros2 service call /stop_recording std_srvs/srv/Trigger

"""

import launch
from launch.actions import DeclareLaunchArgument as LaunchArg
from launch.actions import OpaqueFunction
from launch.substitutions import LaunchConfiguration as LaunchConfig
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode


def make_cameras(cameras, common_params, specific_params):
    return [
        ComposableNode(
            package="metavision_driver",
            plugin="metavision_driver::DriverROS2",
            name=cam,
            parameters=[
                common_params,
                {"serial": specific_params[cam]["serial"]},
                {"sync_mode": specific_params[cam]["sync_mode"]},
            ],
            remappings=specific_params[cam]["remappings"],
            extra_arguments=[{"use_intra_process_comms": True}],
        )
        for cam in cameras
    ]


def make_recorder(cameras, bag_prefix, start_recording_immediately):
    topics = [cam + "/events" for cam in cameras]
    return ComposableNode(
        package="rosbag2_composable_recorder",
        plugin="rosbag2_composable_recorder::ComposableRecorder",
        name="recorder",
        parameters=[{
            "topics": topics,
            "bag_prefix": bag_prefix,
            "storage_id": "sqlite3",
            "serialization_format": "cdr",
            "max_cache_size": 100_000_000,
            "start_recording_immediately": start_recording_immediately,
        }],
        extra_arguments=[{"use_intra_process_comms": True}],
    )


def launch_setup(context, *args, **kwargs):
    primary_name = LaunchConfig("primary_name").perform(context)
    secondary_name = LaunchConfig("secondary_name").perform(context)
    cameras = (primary_name, secondary_name)

    # shared params (bias_file applied to BOTH cameras via common_params,
    # same pattern as the confirmed-working stereo_driver.launch.py)
    common_params = {
        "use_multithreading": LaunchConfig("use_multithreading").perform(context) == "true",
        "bias_file": LaunchConfig("bias_file").perform(context),
        "event_message_time_threshold": 1.0e-3,
    }

    specific_params = {
        primary_name: {
            "serial": LaunchConfig("primary_serial").perform(context),
            "sync_mode": "primary",
            "remappings": [
                ("~/events", primary_name + "/events"),
                # listen for the SECONDARY's ready messages
                ("~/ready", secondary_name + "/ready"),
            ],
        },
        secondary_name: {
            "serial": LaunchConfig("secondary_serial").perform(context),
            "sync_mode": "secondary",
            "remappings": [
                ("~/events", secondary_name + "/events"),
                # secondary's ~/ready is left at its default name —
                # that's exactly what the primary above points at
            ],
        },
    }

    nodes = make_cameras(cameras, common_params, specific_params)
    nodes.append(
        make_recorder(
            cameras,
            LaunchConfig("bag_prefix").perform(context),
            LaunchConfig("start_recording_immediately").perform(context) == "true",
        )
    )

    container = ComposableNodeContainer(
        name="evk4hd_sync_container",
        namespace="",
        package="rclcpp_components",
        executable="component_container_isolated",
        composable_node_descriptions=nodes,
        output="screen",
    )
    return [container]


def generate_launch_description():
    return launch.LaunchDescription([
        LaunchArg("primary_name", default_value="event_camera_primary"),
        LaunchArg("secondary_name", default_value="event_camera_secondary"),
        LaunchArg("primary_serial", default_value="",
                  description="Serial number of the PRIMARY (master) camera"),
        LaunchArg("secondary_serial", default_value="",
                  description="Serial number of the SECONDARY (slave) camera"),
        LaunchArg("bias_file", default_value="",
                  description="Metavision .bias file applied to BOTH cameras"),
        LaunchArg("use_multithreading", default_value="false"),
        LaunchArg("bag_prefix", default_value="evk4hd_sync_bag"),
        LaunchArg("start_recording_immediately", default_value="false"),
        OpaqueFunction(function=launch_setup),
    ])
