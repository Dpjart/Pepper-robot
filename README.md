# Pepper-robot
Using pepper to make a tour robot(confined space)

# Pepper Robot ROS2 Integration

This repository contains the ROS2 integration work for the Pepper robot. The project focuses on connecting Pepper’s NAOqi-based system with ROS2 so that Pepper can perform speech, gestures, person-following, object recognition, mapping, and navigation-related tasks.

Pepper’s official NAOqi driver runs through ROS1, so this system uses a ROS1–ROS2 bridge to allow ROS2 nodes to communicate with Pepper.

---

## Project Goal

The system is designed to support an interactive Pepper robot tour-guide application.

The robot should be able to:


- Navigate through a confined environment
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

## Task 2: Pepper Person Following

This task allows Pepper to listen to "Hey Pepper" using its inbuilt sound localization and turns around to that sound and follows that person.

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

## Task 4: Pepper Exploration Map 

This task focuses on creating a map for navigation using Peppers inbuilt navigation system.

Step 1: Place Pepper in a spce to give tour
Step 2: Place the Artifacts for the tour.
Then run run the codes below

Go to the ROS2 workspace:

```sh
cd ~/p_ws
```

Source ROS2 and the workspace:

```sh
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Run The python file to create the map:

```sh
ros2 run ps exp

```
The generated map will be saved in pepper as a explo file. 

Before going to the next task copy the explo file name, can be seen in the terminal after the follow.py file has completed its task

An example of the file name is 2014-04-04T053142.378Z.explo. (THIS IS AN EXAMPLE DONT USE THIS, YOUR FILE NAME WILL BE DIFFERENT)

## Task 5: Marking the points on the map for the tour.
Before running this make to sure to run pepper talk file in a terminal 
```sh
ros2 run ps ptalk
```
This will establish a connection to the system with the chat bot

Paste the file explo file name in the tour.py file in line 19

EXPLO_FILE = "/home/nao/.local/share/Explorer/2014-04-04T053142.378Z.explo"

and save it.

Continue from the last task 

In the terminal
```sh
ros2 run ps tour
```
It loads a saved Pepper exploration map (`.explo`), localizes Pepper inside the map, saves waypoint positions, and navigates to saved tour points. The node can run a full tour or follow a waypoint order sent from the tablet through the `/tsp_command` topic.

Give It sosme time, it  will take a while to localize in the map.

### Main features

- Connects to Pepper using NAOqi
- Loads a saved `.explo` exploration map
- Relocalizes Pepper in the map
- Saves current Pepper position as numbered waypoints
- Navigates to saved waypoints using `navigateToInMap`
- Receives selected waypoint order from the tablet through `/tsp_command`
- Publishes tour status on `/tour_status`
- Publishes the current point to the talk/explainer system through `/talk_command`
- Waits for `/done_talking` before moving to the next waypoint

## Tour Navigation Commands

After running the tour navigation node, the terminal will show:

```sh
Commands: localize, pos, save, go, tour, list, q
```

Some info for the commands 
pos: current position of the robot
save: save the position as
go: go to the save point
tour: give tour on all this points
list: show the saved points
q: quit

run teleop in another terminal to operate pepper
```sh
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```
Then operate the Pepper to the artifacts location and save those way points.
The waypoints will be saved in a json file. 

If you want to start a tour, type tour in the terminal, in which it will start its tour, from the points.





```md
### ROS 2 topics

| Topic | Type | Purpose |
|---|---|---|
| `/tour_status` | `std_msgs/String` | Publishes current tour status |
| `/artifact_point` | `std_msgs/String` | Publishes reached point ID for artifact/tablet use |
| `/tsp_command` | `social_robot_interfaces/TspCommand` | Receives ordered waypoints from the tablet |
| `/tour_command` | `std_msgs/String` | Receives command such as `start` |
| `/talk_command` | `std_msgs/String` | Sends current waypoint ID to the talking/explainer node |
| `/done_talking` | `std_msgs/String` | Receives confirmation that the explanation is finished |
## Task 6: Pepper Explanation

This task runs Pepper’s explanation behavior.

Go to the ROS2 workspace:

```sh
cd ~/p_ws
```

