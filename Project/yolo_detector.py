import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
import os
import time

class YoloDetector(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        
        # 1. 커스텀 모델 로드
        path = os.path.expanduser('/home/rokey/IsaacSim-ros_workspaces/humble_ws/src/my_pkg/resource/my_best.pt')
        self.model = YOLO(path)
        
        self.bridge = CvBridge()
        
        # 로그 시간 관리용 변수 (초기화)
        self.last_log_time = time.time()
        
        # 아이작 심 카메라 토픽 구독
        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10)
        
        # 클래스 1 탐지 시 트리거를 쏠 퍼블리셔
        self.trigger_pub = self.create_publisher(Bool, '/yolo/detection_trigger', 10)
        
        # 시각화 결과 퍼블리셔
        self.result_pub = self.create_publisher(Image, '/yolo/result_image', 10)
        
        self.get_logger().info('YOLOv8 디텍터 노드가 시작되었습니다.')

    def image_callback(self, msg):
        current_time = time.time()
        # 마지막 로그 출력 후 1초가 지났는지 확인
        can_log = (current_time - self.last_log_time) >= 1.0

        if can_log:
            self.get_logger().info('이미지 토픽 수신됨')

        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            results = self.model(cv_image, conf=0.5, verbose=False)
            
            class_1_detected = False
            
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    if cls_id == 1:
                        class_1_detected = True
                        if can_log: # 탐지 로그도 1초에 한 번만 출력
                            self.get_logger().info('방호복 미착용 인원 탐지됨!')

            # 트리거 상태 발행 (이건 매 프레임 나가는 게 제어에 유리해)
            trigger_msg = Bool()
            trigger_msg.data = class_1_detected
            self.trigger_pub.publish(trigger_msg)

            # 로그를 찍었다면 시간 업데이트
            if can_log:
                self.last_log_time = current_time

            # 시각화 데이터 발행
            annotated_frame = results[0].plot()
            result_msg = self.bridge.cv2_to_imgmsg(annotated_frame, encoding="bgr8")
            self.result_pub.publish(result_msg)

        except Exception as e:
            self.get_logger().error(f'추론 중 오류 발생: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    node = YoloDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('사용자에 의해 노드가 종료되었습니다.')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()