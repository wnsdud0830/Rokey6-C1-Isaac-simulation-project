from nav2_simple_commander.robot_navigator import BasicNavigator
from geometry_msgs.msg import PoseStamped
import rclpy
import time

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

    pose1 = PoseStamped() # cleanroom 간 직후
    pose1.header.frame_id = 'map'
    pose1.pose.position.x = -1.1
    pose1.pose.position.y = 11.1
    
    pose2 = PoseStamped() # cleanroom 순찰
    pose2.header.frame_id = 'map'
    pose2.pose.position.x = -3.5
    pose2.pose.position.y = 16.1
    
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
    
    pose8 = PoseStamped() # packageroom 순찰
    pose8.header.frame_id = 'map'
    pose8.pose.position.x = 1.5
    pose8.pose.position.y = 15.5

    pose9 = PoseStamped() # packageroom 나가기 전
    pose9.header.frame_id = 'map'
    pose9.pose.position.x = 6.75
    pose9.pose.position.y = 9.046513481140137
    
    pose10 = PoseStamped() # 초기 위치
    pose10.header.frame_id = 'map'
    pose10.pose.position.x = -3.0
    pose10.pose.position.y = 3.5
    init_pose.pose.orientation.z = -0.708873
    init_pose.pose.orientation.w = 0.705336
    
    poses = [pose0, pose1, pose2, pose4, pose5, pose6, pose7, pose8, pose9]
    nav.goThroughPoses(poses)
    #---------------------------------------------

    total_poses = len(poses)
    last_stage = None

    while not nav.isTaskComplete():
        feedback = nav.getFeedback()
        if not feedback:
            time.sleep(0.05)
            continue

        remaining = feedback.number_of_poses_remaining
        visited = total_poses - remaining

        # visited 기준
        # 0 : pose0 가는 중
        # 1~3 : pose1~pose4 구간
        # 4 : pose5 가는 중
        # 5~8 : pose6~pose9 구간

        if visited == 0:
            stage = "to_cleanroom"
            msg = "Cleanroom 가는중입니다."
        elif 1 <= visited <= 3:
            stage = "cleanroom_patrol"
            msg = "Cleanroom 순찰중입니다."
        elif visited == 4:
            stage = "to_packageroom"
            msg = "Packageroom에 가는 중입니다."
        else:
            stage = "packageroom_patrol"
            msg = "Packageroom 순찰 중입니다."

        if stage != last_stage:
            nav.get_logger().info(msg)
            last_stage = stage

        time.sleep(0.05)

    # 마지막에 Home 복귀
    nav.get_logger().info("Home 위치로 복귀 중입니다.")
    nav.goToPose(pose10)

    while not nav.isTaskComplete():
        time.sleep(0.05)
            
if __name__ == '__main__':
    main()