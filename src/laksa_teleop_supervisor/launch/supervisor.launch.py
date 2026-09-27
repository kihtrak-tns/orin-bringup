"""Manual-drive supervisor launch. DISABLED BY DEFAULT.

    ros2 launch laksa_teleop_supervisor supervisor.launch.py
        -> node starts but `enabled` parameter is false; publishes nothing.

To actually arm it (only after Phase C's stop-method gate is passed):

    ros2 launch laksa_teleop_supervisor supervisor.launch.py enabled:=true

This file intentionally does not launch a joy_node or any input driver --
wire up whatever gamepad/joystick driver the teammate settles on separately
and point its /joy topic here (remap if needed).
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    enabled_arg = DeclareLaunchArgument(
        "enabled",
        default_value="false",
        description="Must be explicitly set true to arm the supervisor.",
    )
    return LaunchDescription(
        [
            enabled_arg,
            Node(
                package="laksa_teleop_supervisor",
                executable="supervisor_node",
                name="laksa_teleop_supervisor",
                output="screen",
                parameters=[{"enabled": LaunchConfiguration("enabled")}],
            ),
        ]
    )
