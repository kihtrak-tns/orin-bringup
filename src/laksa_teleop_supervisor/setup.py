from setuptools import find_packages, setup

package_name = "laksa_teleop_supervisor"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/supervisor.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="LAKSA team",
    maintainer_email="swathisundaravarathan@gmail.com",
    description="Manual-drive supervisor (disabled by default): deadman, rate limits, stale-input brake.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "supervisor_node = laksa_teleop_supervisor.supervisor_node:main",
        ],
    },
)
