from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='my_pkg',
            executable='yolo_detector',
            name='yolo_detector',
            output='screen'
        ),
        Node(
            package='my_pkg',
            executable='nav_goThrough',
            name='nav_goThrough',
            output='screen'
        ),
    ])