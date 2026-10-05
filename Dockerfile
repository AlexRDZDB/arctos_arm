FROM osrf/ros:jazzy-desktop-full

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-lc"]

WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    terminator \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-joint-state-publisher-gui \
    ros-jazzy-moveit \
    ros-jazzy-moveit-py \
    ros-jazzy-moveit-servo \
    ros-jazzy-ros2-control \
    ros-jazzy-ros2-controllers \
    ros-jazzy-gz-ros2-control \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Run as a user matching the host's UID/GID so files created in the mounted
# workspace are owned by the host user (set UID/GID in .env, see .env.example)
ARG USERNAME=dev
ARG UID=1000
ARG GID=1000

RUN if id ubuntu &>/dev/null; then userdel -r ubuntu; fi \
    && groupadd -o -g ${GID} ${USERNAME} \
    && useradd -o -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && echo "source /opt/ros/jazzy/setup.bash" >> /home/${USERNAME}/.bashrc

USER ${USERNAME}

CMD ["bash"]
