#!/usr/bin/env python3

from platform import node

import qi
import json
import time
import threading
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from social_robot_interfaces.msg import TspCommand

PEPPER_IP = "192.168.0.150"
PEPPER_PORT = 9559

EXPLO_FILE = "/home/nao/.local/share/Explorer/2014-04-04T053142.378Z.explo"
POINTS_FILE = Path("/home/wayfarer/p_ws/src/ps/points.json")


def load_points():
    if POINTS_FILE.exists():
        with open(POINTS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_points(points):
    POINTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(POINTS_FILE, "w") as f:
        json.dump(points, f, indent=4)


def localize(nav):
    print("Relocalizing in map...")
    nav.relocalizeInMap([0.0, 0.0])
    nav.startLocalization()

    print("Waiting for localization to settle...")
    time.sleep(5.0)

    pos = nav.getRobotPositionInMap()[0]
    print("Current map position:")
    print(pos)

    return pos


def face_audience(memory, face_detection, motion, tts):
    subscriber_name = "face_audience_detector"

    print("Starting face detection...")
    face_detection.subscribe(subscriber_name)
    tts.say("Looking for audience")

    try:
        for _ in range(80):
            data = memory.getData("FaceDetected")

            if data and len(data) >= 2 and data[1]:
                print("Face detected. Stopping.")
                motion.stopMove()
                motion.moveToward(0.0, 0.0, 0.0)
                tts.say("Hello everyone")
                return True

            print("No face. Turning slowly...")
            motion.moveToward(0.0, 0.0, 0.12)
            time.sleep(0.1)

        print("No face found.")
        motion.stopMove()
        motion.moveToward(0.0, 0.0, 0.0)
        return False

    finally:
        face_detection.unsubscribe(subscriber_name)


class TourNode(Node):
    def __init__(self):
        super().__init__("pepper_map_points")

        self.status_pub = self.create_publisher(String,"/tour_status",10)

        self.artifact_pub = self.create_publisher(String,"/artifact_point",10)

        self.tsp_sub = self.create_subscription(TspCommand,"/tsp_command",self.tsp_callback,10)

        self.command_sub = self.create_subscription(String,"/tour_command",self.command_callback,10)

        self.talk_command_pub=self.create_publisher(String,"/talk_command",10)

        self.done_talk=self.create_subscription(String,"/done_talking",self.done_talking_callback,10)
        

        self.requested_waypoints = None
        self.start_all_requested = False


    def publish_status(self, text):
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)
        self.get_logger().info(text)

    def publish_artifact_point(self, point_id):
        msg = String()
        msg.data = str(point_id)
        self.artifact_pub.publish(msg)
        self.get_logger().info("Published artifact point: " + str(point_id))

    def tsp_callback(self, msg):
        self.requested_waypoints = [str(wp) for wp in msg.waypoints]
        self.publish_status(
            "Tour requested from tablet: " + str(self.requested_waypoints)
        )

    def command_callback(self, msg):
        command = msg.data.strip().lower()

        if command == "start":
            self.start_all_requested = True
            self.publish_status("Start full tour command received")

    def done_talking_callback(self, msg):
        text = msg.data.strip().lower()
        self.publish_status("Done talking received: " + text)

        if text in ["done", "true", "1", "finished","done_talking"]:
            self.talking_done = True

def wait_for_done_talking(node, timeout=60.0):
    print("Waiting for /done_talking...")
    node.talking_done = False

    start_time = time.time()

    while time.time() - start_time < timeout:
        if node.talking_done:
            print("Talking finished.")
            return True
        time.sleep(0.1)

    print("Timed out waiting for /done_talking")
    return False

def start_tour(points, nav, motion, tts, memory, face_detection, node, waypoint_list=None):
    if not points:
        print("No saved points.")
        node.publish_status("No saved points")
        tts.say("No saved tour points")
        return

    if waypoint_list is None:
        point_ids = sorted(
            points.keys(),
            key=lambda x: int(x) if x.isdigit() else x
        )
    else:
        point_ids = [str(p) for p in waypoint_list]

    print("Tour point order:")
    print(point_ids)

    node.publish_status("Tour started")
    rate = node.create_rate(10)
    tts.say("Starting tour")

    for point_id in point_ids:
        if point_id not in points:
            print("Point not saved:", point_id)
            node.publish_status("Point not saved: " + point_id)
            tts.say("Point " + point_id + " is not saved")
            continue

        target = points[point_id]

        print("Going to point", point_id)
        print(target)

        node.publish_status("Going to point " + point_id)
        tts.say("Going to point " + point_id)

        result = nav.navigateToInMap(target)


        print("Navigation result:", result)
        node.publish_status("Reached point " + point_id)
        tts.say("I reached point " + point_id)

#        face_audience(memory, face_detection, motion, tts)
        node.talk_command_pub.publish(String(data=str(point_id)))
        wait_for_done_talking(node)




#     node.publish_artifact_point(point_id)

        

    node.publish_status("Tour finished")
    tts.say("Tour finished")


def main(args=None):
    rclpy.init(args=args)
    node = TourNode()

    ros_thread = threading.Thread(
        target=rclpy.spin,
        args=(node,),
        daemon=True
    )
    ros_thread.start()

    print("Connecting to Pepper...")
    session = qi.Session()
    session.connect(f"tcp://{PEPPER_IP}:{PEPPER_PORT}")

    nav = session.service("ALNavigation")
    motion = session.service("ALMotion")
    tts = session.service("ALTextToSpeech")
    memory = session.service("ALMemory")
    face_detection = session.service("ALFaceDetection")

    motion.wakeUp()

    print("Loading exploration map:")
    print(EXPLO_FILE)
    nav.loadExploration(EXPLO_FILE)

    localize(nav)

    points = load_points()

    print("Ready.")
    print("Commands: localize, pos, save, go, tour, list, q")
    print("Tablet selected waypoints come from /tsp_command")

    try:
        while True:
            if node.requested_waypoints is not None:
                waypoint_list = node.requested_waypoints
                node.requested_waypoints = None

                points = load_points()
                start_tour(
                    points,
                    nav,
                    motion,
                    tts,
                    memory,
                    face_detection,
                    node,
                    waypoint_list
                )

            if node.start_all_requested:
                node.start_all_requested = False

                points = load_points()
                start_tour(
                    points,
                    nav,
                    motion,
                    tts,
                    memory,
                    face_detection,
                    node
                )

            cmd = input("\nCommand: ").strip().lower()

            if cmd in ["q", "quit", "exit"]:
                break

            elif cmd == "localize":
                localize(nav)

            elif cmd == "pos":
                pos = nav.getRobotPositionInMap()[0]
                print("Current map position:")
                print(pos)

            elif cmd == "save":
                point_id = input("Point number, example 5: ").strip()

                pos = nav.getRobotPositionInMap()[0]
                points[point_id] = pos
                save_points(points)

                print("Saved point", point_id, "=", pos)
                tts.say("Point " + point_id + " saved")
                node.publish_status("Saved point " + point_id)

            elif cmd == "go":
                point_id = input("Go to point number: ").strip()

                if point_id not in points:
                    print("Point not saved:", point_id)
                    continue

                target = points[point_id]

                print("Going to point", point_id)
                print(target)

                tts.say("Going to point " + point_id)
                node.publish_status("Going to point " + point_id)

                result = nav.navigateToInMap(target)

                print("Navigation result:", result)
                tts.say("I reached point " + point_id)
                node.publish_status("Reached point " + point_id)

                face_audience(memory, face_detection, motion, tts)

                node.publish_artifact_point(point_id)

            elif cmd == "tour":
                points = load_points()
                start_tour(
                    points,
                    nav,
                    motion,
                    tts,
                    memory,
                    face_detection,
                    node
                )

            elif cmd == "list":
                print(json.dumps(points, indent=4))

            else:
                print("Unknown command.")
                print("Use: localize, pos, save, go, tour, list, q")

    finally:
        print("Stopping...")
        motion.stopMove()
        motion.moveToward(0.0, 0.0, 0.0)

        try:
            nav.stopLocalization()
        except Exception:
            pass

        rclpy.shutdown()
        print("Done.")


if __name__ == "__main__":
    main()