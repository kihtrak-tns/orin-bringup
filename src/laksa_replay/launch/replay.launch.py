"""Replay a recorded Phase A bag with simulated clock.

    ros2 launch laksa_replay replay.launch.py bag_path:=$HOME/laksa_evidence/run1 rate:=1.0

Nodes consuming replayed data should set use_sim_time:=true to stay in sync
with the bag's clock rather than wall time.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    bag_path_arg = DeclareLaunchArgument("bag_path", default_value="")
    rate_arg = DeclareLaunchArgument("rate", default_value="1.0")

    play = ExecuteProcess(
        cmd=[
            "ros2",
            "bag",
            "play",
            LaunchConfiguration("bag_path"),
            "--clock",
            "--rate",
            LaunchConfiguration("rate"),
        ],
        output="screen",
    )

    return LaunchDescription([bag_path_arg, rate_arg, play])
