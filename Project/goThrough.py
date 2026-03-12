from nav2_simple_commander.robot_navigator import BasicNavigator
from geometry_msgs.msg import PoseStamped
import rclpy

def main():

    rclpy.init()
    # 초기 위치 설정
    nav = BasicNavigator()
    init_pose = PoseStamped()
    init_pose.header.frame_id = 'map'
    init_pose.header.stamp = nav.get_clock().now().to_msg()
    init_pose.pose.position.x = -3.0
    init_pose.pose.position.y = 3.5
    init_pose.pose.orientation.z = -0.708873
    init_pose.pose.orientation.w = 0.705336
        
    nav.setInitialPose(init_pose)
    nav.waitUntilNav2Active()
    
    # #목표지점 설정 --------------------------------
    pose0 = PoseStamped() # cleanroom 가기 직전
    pose0.header.frame_id = 'map'
    pose0.pose.position.x = -6.5
    pose0.pose.position.y = 7.85

    pose1 = PoseStamped() # cleanroom 가기 직전
    pose1.header.frame_id = 'map'
    pose1.pose.position.x = -1.1
    pose1.pose.position.y = 11.1
    
    pose2 = PoseStamped() # cleanroom 통과후
    pose2.header.frame_id = 'map'
    pose2.pose.position.x = -3.5
    pose2.pose.position.y = 16.1
    
    # pose3 = PoseStamped() # cleanroom 순찰
    # pose3.header.frame_id = 'map'
    # pose3.pose.position.x = -11.0
    # pose3.pose.position.y = 13.5
    
    pose4 = PoseStamped() # cleanroom 나가기 전
    pose4.header.frame_id = 'map'
    pose4.pose.position.x = -7.0
    pose4.pose.position.y = 9.500508117675781

    pose5 = PoseStamped() # packageroom 들어가기 전
    pose5.header.frame_id = 'map'
    pose5.pose.position.x = 6.7285306930542
    pose5.pose.position.y = 7.970001220703125
    
    pose6 = PoseStamped() # packageroom 들어간 후
    pose6.header.frame_id = 'map'
    pose6.pose.position.x = 6.618
    pose6.pose.position.y = 10.048
    
    pose7 = PoseStamped() # packageroom 순찰
    pose7.header.frame_id = 'map'
    pose7.pose.position.x = 6.15
    pose7.pose.position.y = 14.560
    
    pose8 = PoseStamped() # packageroom 나가기 전
    pose8.header.frame_id = 'map'
    pose8.pose.position.x = 1.5
    pose8.pose.position.y = 15.5

    pose9 = PoseStamped() # packageroom 나가기 전
    pose9.header.frame_id = 'map'
    pose9.pose.position.x = 6.622818660736084
    pose9.pose.position.y = 8.66513481140137
    
    pose10 = PoseStamped() # 초기 위치
    pose10.header.frame_id = 'map'
    pose10.pose.position.x = -3.0
    pose10.pose.position.y = 3.5
    pose10.pose.orientation.w = 1.0
    
    poses = [pose0, pose1, pose2, pose4, pose5, pose6, pose7, pose8, pose9]
    nav.goThroughPoses(poses)
    #---------------------------------------------

    while not nav.isTaskComplete():
        feedback = nav.getFeedback()
        if feedback:
            print("Goal_distance:", feedback.distance_remaining)

    # 마지막에 초기 위치로 복귀
    nav.goToPose(pose10)
    
    while not nav.isTaskComplete():
        feedback = nav.getFeedback()
        if feedback:
            print("Goal_distance:", feedback.distance_remaining)
            
if __name__ == '__main__':
    main()