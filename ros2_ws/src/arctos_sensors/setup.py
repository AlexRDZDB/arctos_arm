from setuptools import find_packages, setup

package_name = 'arctos_sensors'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Alejandro Rodriguez del Bosque',
    maintainer_email='rodr1674@purdue.edu',
    description='Sensor drivers for the Arctos arm: USB and GigE Vision camera publishers',
    license='BSD-3-Clause',
    entry_points={
        'console_scripts': [
            'camera_publisher = arctos_sensors.camera_publisher:main',
            'gige_camera_publisher = arctos_sensors.gige_camera_publisher:main',
        ],
    },
)
