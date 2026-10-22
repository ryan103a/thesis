#!/usr/bin/env python3
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode


def launch_setup(context, *args, **kwargs):
    # .perform(context) resolves a LaunchConfiguration to a plain Python str
    camera_name = LaunchConfiguration('camera_name').perform(context)
    event_topic = LaunchConfiguration('event_topic').perform(context)
    bag_prefix = LaunchConfiguration('bag_prefix').perform(context)
    bias_file = LaunchConfiguration('bias_file').perform(context)
    use_multithreading = LaunchConfiguration('use_multithreading').perform(context) == 'true'
    start_recording_immediately = (
        LaunchConfiguration('start_recording_immediately').perform(context) == 'true'
    )

    container = ComposableNodeContainer(
        name='evk4hd_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container_mt',
        composable_node_descriptions=[
            ComposableNode(
                package='metavision_driver',
                plugin='metavision_driver::DriverROS2',
                name=camera_name,
                parameters=[{
                    'bias_file': bias_file,
                    'use_multithreading': use_multithreading,
                    'statistics_print_interval': 5.0,
                }],
                remappings=[('events', event_topic)],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
            ComposableNode(
                package='rosbag2_composable_recorder',
                plugin='rosbag2_composable_recorder::ComposableRecorder',
                name='recorder',
                parameters=[{
                    'topics': [event_topic],   # <- now a real list[str], resolved above
                    'bag_prefix': bag_prefix,
                    'storage_id': 'sqlite3',
                    'serialization_format': 'cdr',
                    'max_cache_size': 100_000_000,
                    'start_recording_immediately': start_recording_immediately,
                }],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
        ],
        output='screen',
    )
    return [container]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('camera_name', default_value='event_camera'),
        DeclareLaunchArgument('event_topic', default_value='event_camera/events'),
        DeclareLaunchArgument('bag_prefix', default_value='evk4hd_bag'),
        DeclareLaunchArgument('bias_file', default_value=''),
        DeclareLaunchArgument('use_multithreading', default_value='false'),
        DeclareLaunchArgument('start_recording_immediately', default_value='false'),
        OpaqueFunction(function=launch_setup),
    ])
