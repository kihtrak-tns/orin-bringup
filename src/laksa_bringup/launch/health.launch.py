"""Boot-safe launch: starts ONLY the listen-only health check.

Deliberately does not start, include, or depend on any node that publishes
to /laksa/command, /laksa/brake, or any SetDriveCommand service call.
The micro-ROS agent itself is started as a separate systemd unit
(see ../systemd/laksa-microros-agent.service), not from this launch file,
so that a `ros2 launch` failure here can never take the agent down with it.
"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="laksa_bringup",
                executable="laksa_health",
                name="laksa_health",
                output="screen",
            ),
        ]
    )
