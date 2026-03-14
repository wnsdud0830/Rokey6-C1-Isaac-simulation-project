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
        
        # 커스텀 모델 로드
        path = os.path.expanduser('/home/rokey/IsaacSim-ros_workspaces/humble_ws/src/my_pkg/resource/my_best.pt')
        self.model = YOLO(path)
        
        self.bridge = CvBridge()

        # 로그 쿨다운 시간(초)
        self.log_cooldown = 13.0

        # 각 클래스별 마지막 로그 출력 시각
        self.last_class_0_log_time = 0.0
        self.last_class_1_log_time = 0.0
        
        # 아이작 심 카메라 토픽 구독
        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10)
        
        # 클래스 0 탐지 시 트리거 퍼블리셔
        self.trigger_pub = self.create_publisher(Bool, '/yolo/detection_trigger', 10)
        
        # 시각화 결과 퍼블리셔
        self.result_pub = self.create_publisher(Image, '/yolo/result_image', 10)
        
        self.get_logger().info('YOLOv8 디텍터 노드가 시작되었습니다.')

    def image_callback(self, msg):
        try:
            current_time = time.time()

            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            results = self.model(cv_image, conf=0.7, verbose=False)
            
            class_0_detected = False
            class_1_detected = False
            
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])

                    if cls_id == 0:
                        class_0_detected = True
                    elif cls_id == 1:
                        class_1_detected = True

            # 클래스 0 로그: 쿨다운 지난 경우만 출력
            if class_0_detected:
                if current_time - self.last_class_0_log_time >= self.log_cooldown:
                    self.get_logger().info('방호복 미착용 인원 탐지됨!')
                    self.last_class_0_log_time = current_time

            # 클래스 1 로그: 쿨다운 지난 경우만 출력
            if class_1_detected:
                if current_time - self.last_class_1_log_time >= self.log_cooldown:
                    self.get_logger().info('작업자 인식!')
                    self.last_class_1_log_time = current_time

            # 트리거 상태 발행 (클래스 0 기준)
            trigger_msg = Bool()
            trigger_msg.data = class_0_detected
            self.trigger_pub.publish(trigger_msg)

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