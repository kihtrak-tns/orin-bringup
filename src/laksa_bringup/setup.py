from setuptools import find_packages, setup

package_name = "laksa_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", [
            "launch/health.launch.py",
            "launch/record_bags.launch.py",
        ]),
        (f"share/{package_name}/systemd", [
            "systemd/laksa-microros-agent.service",
            "systemd/laksa-health.service",
        ]),
        (f"share/{package_name}/udev", ["udev/99-laksa.rules"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="LAKSA team",
    maintainer_email="swathisundaravarathan@gmail.com",
    description="Boot-safe bringup, health check, and A1 verification tooling for LAKSA.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "laksa_health = laksa_bringup.laksa_health:main",
            "laksa_readonly_check = laksa_bringup.laksa_readonly_check:main",
            "drive_command_loopback_test = laksa_bringup.drive_command_loopback_test:main",
        ],
    },
)
