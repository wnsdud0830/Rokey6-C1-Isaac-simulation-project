from nav2_simple_commander.robot_navigator import BasicNavigator
from geometry_msgs.msg import PoseStamped
import rclpy

def main():

    rclpy.init()
    nav = BasicNavigator()
    # 1. 異쒕컻�� �ㅼ젙
    init_pose = PoseStamped()
    init_pose.header.frame_id = 'map'
    
    nav.setInitialPose(init_pose)
    nav.waitUntilNav2Active()
    
    # 2. 紐⑺몴 吏��� �ㅼ젙
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.pose.position.x = 2.0
    pose.pose.position.y = 3.0
    pose.pose.orientation.w = 1.0

    nav.goToPose(pose)
    
    while not nav.isTaskComplete():
        feedback = nav.getFeedback()
        if feedback:
            print("Goal_distance:", feedback.distance_remaining)
            
if __name__ == '__main__':
    main()