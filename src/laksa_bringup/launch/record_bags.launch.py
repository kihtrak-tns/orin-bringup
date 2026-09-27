"""A6 helper: record rosbags for later replay (Phase E preparation).

NOT part of boot. Run manually:

    ros2 launch laksa_bringup record_bags.launch.py \
        out_dir:=$HOME/laksa_evidence/$(date +%Y%m%d_%H%M%S)_static

Records the topics needed for the Phase A replay pipeline: vehicle/VESC/
steering state (listen-only, always safe to record), IMU, and -- once A2/A5
land -- LiDAR /scan and the ZED topics. The lidar/zed topic names are left as
launch arguments since their exact names depend on the driver configuration
chosen in A2/A5, which are still open per orin_bringup_plan.md.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration

CORE_TOPICS = [
    "/laksa/state",
    "/laksa/vesc/state",
    "/laksa/pca9685/state",
    "/laksa/imu/data",
    "/laksa/imu/mag",
    "/laksa/brake",
]


def generate_launch_description() -> LaunchDescription:
    out_dir_arg = DeclareLaunchArgument(
        "out_dir",
        default_value="",
        description="rosbag output directory (required, no default on purpose)",
    )
    lidar_topic_arg = DeclareLaunchArgument("lidar_topic", default_value="/scan")
    zed_topics_arg = DeclareLaunchArgument(
        "zed_topics",
        default_value="",
        description="space-separated extra ZED topics to include once A5 lands",
    )
    include_lidar_arg = DeclareLaunchArgument("include_lidar", default_value="false")
    include_zed_arg = DeclareLaunchArgument("include_zed", default_value="false")

    def build_cmd(context):
        topics = list(CORE_TOPICS)
        if LaunchConfiguration("include_lidar").perform(context) == "true":
            topics.append(LaunchConfiguration("lidar_topic").perform(context))
        if LaunchConfiguration("include_zed").perform(context) == "true":
            extra = LaunchConfiguration("zed_topics").perform(context).split()
            topics.extend(extra)
        out_dir = LaunchConfiguration("out_dir").perform(context)
        if not out_dir:
            raise RuntimeError("out_dir launch argument is required, e.g. "
                                "out_dir:=$HOME/laksa_evidence/run1")
        return ["ros2", "bag", "record", "-o", out_dir] + topics

    from launch.actions import OpaqueFunction

    def launch_setup(context, *args, **kwargs):
        cmd = build_cmd(context)
        return [ExecuteProcess(cmd=cmd, output="screen")]

    return LaunchDescription(
        [
            out_dir_arg,
            lidar_topic_arg,
            zed_topics_arg,
            include_lidar_arg,
            include_zed_arg,
            OpaqueFunction(function=launch_setup),
        ]
    )
