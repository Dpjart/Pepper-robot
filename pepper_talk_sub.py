#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import urllib.request
import qi

PEPPER_IP = "192.168.0.150"
PEPPER_PORT = 9559

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"


class PepperLink(Node):
    def __init__(self):
        super().__init__('pepper_link')
        self.subscriber_ = self.create_subscription(String, '/speech_content',self.speak_callback_,10)
        self.subscriber1_ = self.create_subscription(String,'/speech/intent', self.intent_parser_,10)
        # Publisher to start tour
        self.tour_pub = self.create_publisher(String,'/tour_command',10)

        print("Connecting to Pepper...")

        self.session = qi.Session()
        self.session.connect("tcp://{}:{}".format(PEPPER_IP, PEPPER_PORT))

        self.tts = self.session.service("ALTextToSpeech")
        
        self.tts.setLanguage("English")
        self.tts.setVolume(0.8)

        print("Connected to Pepper.")
        self.subscriber_

    def speak_callback_(self, msg):
        self.get_logger().info('I heard: "%s"' % msg.data)
        self.tts.say(msg.data)
    
    def intent_parser_(self,msg):
        msg_=msg.data
        msg_=json.loads(msg_)
        intent=msg_['intent']
        self.get_logger().info('Parsed intent: "%s"' % intent)
        if intent == "start_tour":
            self.get_logger().info('Publishing start tour command')
            command_msg = String()
            command_msg.data = "start"
            self.tour_pub.publish(command_msg)  
        

def main(args=None):
    rclpy.init(args=args)
    minimal_subscriber = PepperLink()
    rclpy.spin(minimal_subscriber)
    minimal_subscriber.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
    


