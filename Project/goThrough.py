from nav2_simple_commander.robot_navigator import BasicNavigator
from geometry_msgs.msg import PoseStamped
import rclpy

def main():

    rclpy.init()
    # 초기 위치 설정
    nav = BasicNavigator()
    init_pose = PoseStamped()
    init_pose.header.frame_id = 'map'
    
    nav.setInitialPose(init_pose)
    nav.waitUntilNav2Active()
    
    #목표지점 설정 --------------------------------
    pose1 = PoseStamped() # 경유지 1
    pose1.header.frame_id = 'map'
    pose1.pose.position.x = -3.4
    pose1.pose.position.y = 3.2
    
    pose2 = PoseStamped() # 경유지 2
    pose2.header.frame_id = 'map'
    pose2.pose.position.x = -2.7
    pose2.pose.position.y = -1.3
    
    pose3 = PoseStamped() # 최종 목적지
    pose3.header.frame_id = 'map'
    pose3.pose.position.x = 2.6
    pose3.pose.position.y = -0.5
    pose3.pose.orientation.w = 1.0
    
    poses = [pose1, pose2, pose3]
    nav.goThroughPoses(poses)
		#---------------------------------------------
    while not nav.isTaskComplete():
        feedback = nav.getFeedback()
        if feedback:
            print("Goal_distance:", feedback.distance_remaining)
            
if __name__ == '__main__':
    main()