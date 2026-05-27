#!/usr/bin/env python3

import time
import math
import qi
import rclpy

from .wav import PepperWaveReal


PEPPER_IP = "192.168.0.150"
PEPPER_PORT = 9559

COMMAND_PHRASE = "follow me pepper"
COMMAND_CONFIDENCE = 0.35

FOLLOW_DISTANCE = 0.8
STOP_DISTANCE = 0.45

# moveToward uses normalized speeds, not real m/s.
# Keep these low so Pepper does not rush past the person.
MAX_FORWARD_SPEED = 0.35
MAX_TURN_SPEED = 0.45

FORWARD_GAIN = 0.35
TURN_GAIN = 0.8

SOUND_CONFIDENCE_MIN = 0.25
MAX_SOUND_TURN = 1.2          # radians, about 69 degrees
PERSON_SEARCH_TIME = 8.0      # seconds after turning to find a person


class PepperVoiceFollow:
    def __init__(self):
        self.session = qi.Session()
        self.session.connect(f"tcp://{PEPPER_IP}:{PEPPER_PORT}")

        self.motion = self.session.service("ALMotion")
        self.memory = self.session.service("ALMemory")
        self.tts = self.session.service("ALTextToSpeech")
        self.people = self.session.service("ALPeoplePerception")
        self.tracker = self.session.service("ALTracker")
        self.asr = self.session.service("ALSpeechRecognition")
        self.sound_loc = self.session.service("ALSoundLocalization")

        self.wave_gesture = PepperWaveReal()

        self.current_target_id = None
        self.follow_mode = False
        self.has_waved = False

        self.motion.wakeUp()

        # People detection
        self.people.subscribe("voice_follow_people")

        # Head tracker setup
        self.tracker.stopTracker()
        self.tracker.unregisterAllTargets()

        # Speech recognition setup
        try:
            self.asr.pause(True)
            self.asr.setLanguage("English")
            self.asr.setVocabulary([COMMAND_PHRASE], True)
            self.asr.setAudioExpression(False)
            self.asr.setVisualExpression(True)
            self.asr.pause(False)
            self.asr.subscribe("voice_follow_asr")
        except Exception as e:
            print("ASR setup failed:", e)

        # Sound localization setup
        try:
            self.sound_loc.setParameter("Sensitivity", 0.7)
            self.sound_loc.subscribe("voice_follow_sound")
        except Exception as e:
            print("Sound localization setup failed:", e)

        print("Voice follow started.")
        print(f'Say: "{COMMAND_PHRASE}"')
        print("Pepper will turn to the voice, wave, then follow the detected person.")

    def clamp(self, value, low, high):
        return max(low, min(high, value))

    def get_word_recognized(self):
        try:
            data = self.memory.getData("WordRecognized")
            if data in [None, [], 0, -1]:
                return None, 0.0

            # Format: [phrase_1, confidence_1, phrase_2, confidence_2, ...]
            phrase = str(data[0]).lower()
            confidence = float(data[1])

            return phrase, confidence

        except Exception as e:
            print("Could not read WordRecognized:", e)
            return None, 0.0

    def command_heard(self):
        phrase, confidence = self.get_word_recognized()

        if phrase is None:
            return False

        print(f"Recognized: {phrase}, confidence={confidence:.2f}")

        return COMMAND_PHRASE in phrase and confidence >= COMMAND_CONFIDENCE

    def get_sound_angle(self):
        try:
            data = self.memory.getData("ALSoundLocalization/SoundLocated")

            if data in [None, [], 0, -1]:
                return None

            # Pepper format:
            # [
            #   [time_sec, time_usec],
            #   [azimuth_rad, elevation_rad, confidence],
            #   [head position 6D]
            # ]
            sound_info = data[1]
            azimuth = float(sound_info[0])
            elevation = float(sound_info[1])
            confidence = float(sound_info[2])

            print(
                f"Sound located: azimuth={azimuth:.2f}, "
                f"elevation={elevation:.2f}, confidence={confidence:.2f}"
            )

            if confidence < SOUND_CONFIDENCE_MIN:
                print("Sound confidence too low.")
                return None

            return azimuth

        except Exception as e:
            print("Could not read sound location:", e)
            return None

    def turn_to_voice(self):
        print("Turning toward voice...")

        azimuth = None

        # Give sound localization a short moment to update after the command.
        start = time.time()
        while time.time() - start < 2.0:
            azimuth = self.get_sound_angle()
            if azimuth is not None:
                break
            time.sleep(0.1)

        if azimuth is None:
            print("No reliable sound direction found. I will not turn.")
            return

        # Clamp so Pepper does not spin too much from one noisy reading.
        turn_angle = self.clamp(azimuth, -MAX_SOUND_TURN, MAX_SOUND_TURN)

        print(f"Body turning by {turn_angle:.2f} rad")

        try:
            self.motion.moveToward(0.0, 0.0, 0.0)
            self.motion.moveTo(0.0, 0.0, turn_angle)
            time.sleep(0.5)
        except Exception as e:
            print("Turn to voice failed:", e)

    def get_people_list(self):
        try:
            people_list = self.memory.getData("PeoplePerception/PeopleList")
            if people_list in [None, [], 0, -1]:
                return []
            return list(people_list)
        except Exception as e:
            print("Could not read PeopleList:", e)
            return []

    def get_person_position(self, person_id):
        try:
            key = f"PeoplePerception/Person/{person_id}/PositionInRobotFrame"
            pos = self.memory.getData(key)

            if pos in [None, [], 0, -1]:
                return None

            return pos

        except Exception as e:
            print(f"Could not read position for person {person_id}:", e)
            return None

    def choose_best_person_in_front(self):
        people_list = self.get_people_list()

        if len(people_list) == 0:
            return None

        best_id = None
        best_score = 999.0

        for person_id in people_list:
            pos = self.get_person_position(person_id)

            if pos is None or len(pos) < 2:
                continue

            x = float(pos[0])
            y = float(pos[1])

            # Ignore weird positions behind Pepper.
            if x <= 0.2:
                continue

            # Prefer whoever is closest to Pepper's front center.
            score = abs(y) + (0.15 * x)

            print(f"Candidate person {person_id}: x={x:.2f}, y={y:.2f}, score={score:.2f}")

            if score < best_score:
                best_score = score
                best_id = person_id

        return best_id

    def wait_for_person_after_turn(self):
        print("Looking for the person who spoke...")

        start = time.time()

        while time.time() - start < PERSON_SEARCH_TIME:
            person_id = self.choose_best_person_in_front()

            if person_id is not None:
                print(f"Selected person ID: {person_id}")
                return person_id

            print("No person found yet.")
            time.sleep(0.3)

        print("Could not find a person after turning.")
        return None

    def start_head_tracking(self, person_id):
        try:
            self.tracker.stopTracker()
            self.tracker.unregisterAllTargets()

            self.tracker.registerTarget("People", [person_id])
            self.tracker.setMode("Head")
            self.tracker.track("People")

            print(f"Head tracking person ID: {person_id}")

        except Exception as e:
            print(f"Could not head-track person {person_id}:", e)

    def wave_once(self):
        if self.has_waved:
            return

        try:
            self.motion.moveToward(0.0, 0.0, 0.0)

            # Pause ASR while Pepper speaks, otherwise it can hear itself.
            try:
                self.asr.pause(True)
            except Exception:
                pass

            self.tts.say("Okay, I will follow you.")
            self.wave_gesture.wave_motion()

            try:
                self.asr.pause(False)
            except Exception:
                pass

            self.has_waved = True

        except Exception as e:
            print("Wave failed:", e)

    def follow_person(self, person_id):
        pos = self.get_person_position(person_id)

        if pos is None or len(pos) < 2:
            print("Lost target. Stopping.")
            self.motion.moveToward(0.0, 0.0, 0.0)
            return False

        x = float(pos[0])
        y = float(pos[1])

        print(f"Target position x={x:.2f}, y={y:.2f}")

        distance_error = x - FOLLOW_DISTANCE

        if x < STOP_DISTANCE:
            forward_speed = 0.0
        else:
            forward_speed = self.clamp(
                distance_error * FORWARD_GAIN,
                0.0,
                MAX_FORWARD_SPEED
            )

        turn_speed = self.clamp(
            y * TURN_GAIN,
            -MAX_TURN_SPEED,
            MAX_TURN_SPEED
        )

        self.motion.moveToward(
            float(forward_speed),
            0.0,
            float(turn_speed)
        )

        print(f"Move forward={forward_speed:.2f}, turn={turn_speed:.2f}")

        return True

    def activate_follow_mode(self):
        self.motion.moveToward(0.0, 0.0, 0.0)

        self.turn_to_voice()

        person_id = self.wait_for_person_after_turn()

        if person_id is None:
            try:
                self.tts.say("I heard you, but I cannot see you.")
            except Exception:
                pass
            return

        self.current_target_id = person_id
        self.follow_mode = True
        self.has_waved = False

        self.start_head_tracking(self.current_target_id)
        self.wave_once()

    def run(self):
        try:
            while True:
                if not self.follow_mode:
                    if self.command_heard():
                        print("Follow command heard.")
                        self.activate_follow_mode()
                    else:
                        self.motion.moveToward(0.0, 0.0, 0.0)

                    time.sleep(0.2)
                    continue

                people_list = self.get_people_list()

                if self.current_target_id not in people_list:
                    print("Target lost from PeopleList. Trying to reacquire.")
                    self.motion.moveToward(0.0, 0.0, 0.0)

                    new_target = self.choose_best_person_in_front()

                    if new_target is not None:
                        self.current_target_id = new_target
                        self.start_head_tracking(self.current_target_id)
                    else:
                        time.sleep(0.3)
                        continue

                self.follow_person(self.current_target_id)

                time.sleep(0.2)

        except KeyboardInterrupt:
            print("Stopping...")

        self.stop()

    def stop(self):
        try:
            self.motion.moveToward(0.0, 0.0, 0.0)
        except Exception:
            pass

        try:
            self.tracker.stopTracker()
            self.tracker.unregisterAllTargets()
        except Exception:
            pass

        try:
            self.people.unsubscribe("voice_follow_people")
        except Exception:
            pass

        try:
            self.asr.unsubscribe("voice_follow_asr")
        except Exception:
            pass

        try:
            self.sound_loc.unsubscribe("voice_follow_sound")
        except Exception:
            pass


def main(args=None):
    rclpy.init(args=args)

    app = PepperVoiceFollow()

    try:
        app.run()
    except KeyboardInterrupt:
        pass

    app.stop()
    rclpy.shutdown()


if __name__ == "__main__":
    main()