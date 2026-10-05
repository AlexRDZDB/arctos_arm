from glob import glob

from setuptools import find_packages, setup

package_name = 'arctos_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Alejandro Rodriguez del Bosque',
    maintainer_email='rodr1674@purdue.edu',
    description='Pose tracking for the Arctos arm with MoveIt planning and MoveIt Servo',
    license='BSD-3-Clause',
    entry_points={
        'console_scripts': [
            'carrot_on_a_stick_controller = arctos_control.carrot_on_a_stick_controller:main',
            'figure_eight_publisher = arctos_control.figure_eight_publisher:main',
        ],
    },
)
