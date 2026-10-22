import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

# Hard-coded event camera settings
PRIMARY_SERIAL = '00052135'     # replace with your serial
SECONDARY_SERIAL = '00052136'   # replace with your serial
PRIMARY_SETTINGS = ''           # optional settings/bias file path
SECONDARY_SETTINGS = ''
BIAS_FILE = '/home/bluerov/ryan/config/checkerboard.bias'


def include(pkg, launch_file, args=None):
    path = os.path.join(get_package_share_directory(pkg), 'launch', launch_file)
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(path),
        launch_arguments=(args or {}).items(),
    )


def generate_launch_description():
    sensors = [
        include('oculus_ros2', 'default.launch.py'),
        include('waterlinked_dvl_driver', 'dvl.launch.py'),
        include('bluerov_ros2', 'bluerov2_bringup.launch.py'),
        include('zed_wrapper', 'zed_camera.launch.py', {'camera_model': 'zed2i'}),
    ]

    secondary_camera = Node(
        package='metavision_driver',
        executable='driver_node',
        name='event_camera_secondary',
        output='screen',
        parameters=[{
            'serial': SECONDARY_SERIAL,
            'sync_mode': 'secondary',
            'settings': SECONDARY_SETTINGS,
            'bias_file': BIAS_FILE,
            'statistics_print_interval': 2.0,
        }],
    )

    primary_camera = Node(
        package='metavision_driver',
        executable='driver_node',
        name='event_camera_primary',
        output='screen',
        parameters=[{
            'serial': PRIMARY_SERIAL,
            'sync_mode': 'primary',
            'settings': PRIMARY_SETTINGS,
            'bias_file': BIAS_FILE,
            'statistics_print_interval': 2.0,
        }],
        # the primary waits for the secondary's ready signal
        remappings=[('~/ready', '/event_camera_secondary/ready')],
    )

    return LaunchDescription(sensors + [secondary_camera, primary_camera])