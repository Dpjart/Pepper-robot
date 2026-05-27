#!/usr/bin/env python3

import qi
import time

PEPPER_IP = "192.168.0.150"
PEPPER_PORT = 9559

# Exploration radius in meters
EXPLORATION_RADIUS = 10.0


def main():
    print("Connecting to Pepper...")
    session = qi.Session()
    session.connect(f"tcp://{PEPPER_IP}:{PEPPER_PORT}")

    nav = session.service("ALNavigation")
    motion = session.service("ALMotion")
    tts = session.service("ALTextToSpeech")

    print("Connected.")
    motion.wakeUp()

    tts.say("I am starting exploration")
    print("Starting exploration with radius:", EXPLORATION_RADIUS)

    result = nav.explore(EXPLORATION_RADIUS)

    print("Explore result:", result)

    print("Saving exploration map...")
    explo_path = nav.saveExploration()

    print("Saved exploration file:")
    print(explo_path)

    tts.say("Exploration saved")

    print("Stopping localization just in case...")
    try:
        nav.stopLocalization()
    except Exception:
        pass

    motion.moveToward(0.0, 0.0, 0.0)

    print("Done.")


if __name__ == "__main__":
    main()