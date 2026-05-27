# Pepper-robot
Using pepper to make a tour robot(confined space)

# Pepper Robot ROS2 Integration

This repository contains the ROS2 integration work for the Pepper robot. The project focuses on connecting Pepper’s NAOqi-based system with ROS2 so that Pepper can perform speech, gestures, person-following, object recognition, mapping, and navigation-related tasks.

Pepper’s official NAOqi driver runs through ROS1, so this system uses a ROS1–ROS2 bridge to allow ROS2 nodes to communicate with Pepper.

---

## Project Goal

The system is designed to support an interactive Pepper robot tour-guide application.

The robot should be able to:

- Greet visitors and initiate guided tours
- Navigate safely through dynamic and crowded environments
- Provide explanations and contextual information at designated locations
- Respond to voice commands and basic conversational prompts
- Use gestures and expressive behaviours to create a welcoming interaction

The ultimate goal is to deliver a reliable, interactive, and user-friendly tour-guide system that enhances visitor engagement while reducing the operational workload for staff.

---

## Hardware and Software

Pepper is a humanoid robot developed by SoftBank Robotics. It includes onboard sensors and interaction hardware such as:

- Tablet display
- Speakers and microphones
- Cameras
- Sonar sensors
- Laser sensor
- Head, torso, and arm joints
- NAOqi software framework

An external laptop is used to develop and run the ROS2 side of the system. The laptop connects to Pepper through the NAOqi driver.

Since Pepper uses NAOqi version 2.5, the Pepper NAOqi driver runs in ROS1. A ROS1–ROS2 bridge is then used to connect Pepper’s ROS1 topics and services to the ROS2 workspace.

---

## Main Software Stack

- Ubuntu 22.04
- ROS2 Humble
- ROS Noetic
- ROS1–ROS2 Bridge
- NAOqi Driver
- Python 3
- Docker

---

## Dependencies

### Install Docker

Docker is used to run the ROS1 Noetic environment required by the Pepper NAOqi driver.

Follow the official Docker installation guide for Ubuntu:

https://docs.docker.com/desktop/setup/install/linux/ubuntu/

### Install NAOqi Driver inside Docker

Inside the ROS Noetic Docker environment, install the Pepper NAOqi driver:

```sh
sudo apt update
sudo apt install ros-noetic-naoqi-driver
```

---

## Running the System

### Task 1: Establish Connection with Pepper

First, open the Docker container with ROS1 Noetic.

Source the ROS1 environment inside Docker:

```sh
source /opt/ros/noetic/setup.bash
```

Start the Pepper NAOqi driver:

```sh
roslaunch naoqi_driver naoqi_driver.launch \
  nao_ip:=192.168.0.150 \
  nao_port:=9559 \
  roscore_ip:=192.168.0.185 \
  network_interface:=wlo1
```

Use the following commands to verify that the Pepper driver is running:

```sh
rosnode list
rostopic list
```

If the connection is working, Pepper-related topics should appear.

---

### Bridge ROS1 to ROS2

On the host laptop, source ROS2 Humble:

```sh
source /opt/ros/humble/setup.bash
```

Source the ROS1–ROS2 bridge workspace:

```sh
source ~/ros-humble-ros1-bridge/install/local_setup.bash
```

Run the dynamic bridge:

```sh
ros2 run ros1_bridge dynamic_bridge --bridge-all-topics
```

This allows communication between ROS1 Pepper topics and ROS2 nodes.

---

### Direct SSH Connection to Pepper

To directly connect to Pepper’s terminal:

```sh
ssh nao@<pepper_ip>
```

For example:

```sh
ssh nao@192.168.0.150
```

Useful Pepper commands:

```sh
qicli call ALAutonomousLife.setState "disabled"
qicli call ALMotion.wakeUp
```

These commands disable autonomous life and wake up Pepper’s motors.

---

## Task 2: Pepper Speech with Explanation Gesture

This task makes Pepper speak while performing an explanation gesture.

Go to the ROS2 workspace:

```sh
cd ~/p_ws
```

Source ROS2:

```sh
source /opt/ros/humble/setup.bash
```

Source the workspace:

```sh
source install/setup.bash
```

Run the node:

```sh
ros2 run ps wave
```

Expected result:

Pepper will speak and perform an explaining gesture related to the artifact or presentation content.

Known issues:

No known issues have been noticed in this task.

---

## Task 3: Pepper Person Following

This task allows Pepper to detect a person, wave, and then follow the person.

Go to the ROS2 workspace:

```sh
cd ~/p_ws
```

Source the workspace:

```sh
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Run the node:

```sh
ros2 run ps follow
```

Expected result:

Pepper will wave at the detected person and then begin following them.

Known issues:

No known issues have been noticed in this task.

---

## Task 4: Pepper Exploration Map and Navigation

This task focuses on creating a map for navigation using SLAM Toolbox.

This part of the system is still a work in progress.

Go to the ROS2 workspace:

```sh
cd ~/p_ws
```

Source ROS2 and the workspace:

```sh
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Run SLAM Toolbox:

```sh
ros2 run slam_toolbox async_slam_toolbox_node \
  --ros-args \
  -p odom_frame:=odom \
  -p base_frame:=base_footprint \
  -p map_frame:=map \
  -p minimum_laser_range:=0.1 \
  -p max_laser_range:=10.0 \
  -p transform_timeout:=0.5
```

Save the generated map:

```sh
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "{name: {data: '/home/wayfarer/p_ws/src/ps/maps/pepper_slam_map'}}"
```

Launch Nav2 using the saved map:

```sh
ros2 launch nav2_bringup bringup_launch.py \
  map:=/home/wayfarer/p_ws/src/ps/maps/pepper_slam_map.yaml \
  params_file:=/home/wayfarer/p_ws/src/ps/config/nav2_params.yaml \
  use_sim_time:=false
```

Known issues:

Pepper’s laser sensor provides only around 60 laser points, while the SLAM setup expects 64 laser points. Because of this, an additional correction node is run alongside the SLAM system:

```sh
ros2 run ps say
```

Pepper’s laser sensor is older and requires further tuning for stable SLAM and navigation. This part still needs more testing and improvement.

---

## Task 5: Train and Detect Object

This task uses Pepper’s vision recognition system to train and detect a specific object.

Go to the ROS2 workspace:

```sh
cd ~/p_ws
```

Source ROS2 and the workspace:

```sh
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Take images of the required object.

Save the images on Pepper at:

```sh
/home/nao/artifacts/
```

Run the training node from the ROS2 side:

```sh
ros2 run ps train
```

To detect the trained object:

```sh
ros2 run ps detect
```

Expected result:

Pepper should detect the trained object when it is visible to the camera.

---

## Task 6: Pepper Explanation

This task runs Pepper’s explanation behavior.

Go to the ROS2 workspace:

```sh
cd ~/p_ws
```

Source ROS2 and the workspace:

```sh
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Run the explanation node:

```sh
ros2 run ps gat
```

Expected result:

Pepper will perform the explanation behavior using speech and interaction features.

---

## Current Status

The system currently supports:

- ROS1 NAOqi driver connection
- ROS1–ROS2 topic bridging
- Pepper speech
- Pepper gestures
- Person following
- Object training and detection
- Initial SLAM and map saving experiments
- Early Nav2 integration

Navigation and SLAM are still under development due to limitations with Pepper’s onboard laser sensor and the need for additional parameter tuning.

---

## Known Limitations

- Pepper’s NAOqi driver runs in ROS1, requiring a ROS1–ROS2 bridge.
- SLAM and Nav2 integration are still unstable.
- Pepper’s laser sensor has a low number of scan points.
- Navigation requires further testing in real environments.
- Some behaviours depend on Pepper’s physical condition, network stability, and correct NAOqi service availability.
