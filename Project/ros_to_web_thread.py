import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
import json
import asyncio
import websockets
import threading
import time

class RosToWebSender(Node):
    def __init__(self):
        super().__init__('ros_to_web_sender')
        self.uri = "ws://192.168.189.132:8000/ws" 
        
        # 비동기 루프와 큐를 보관할 변수
        self.loop = None
        self.queue = None
        
        self.create_subscription(String, '/robot_status', self.status_callback, 10)
        self.create_subscription(String, '/door_status', self.status_callback, 10)
        self.create_subscription(String, '/yolo/detection_text', self.yolo_text_callback, 10)
        
        self.last_yolo_time = 0

        # 별도 스레드 시작
        threading.Thread(target=self.start_async_loop, daemon=True).start()
        self.get_logger().info("=== Thread-Safe Log Sender Initialized ===")

    def start_async_loop(self):
        # 이 스레드 전용 루프와 큐 생성
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.queue = asyncio.Queue()
        
        self.loop.run_until_complete(self.socket_worker())

    async def socket_worker(self):
        while rclpy.ok():
            try:
                self.get_logger().info(f"Connecting to {self.uri}...")
                async with websockets.connect(self.uri, ping_interval=None) as websocket:
                    self.get_logger().info("Connected! (Socket Ready)")
                    
                    # 연결 성공 테스트 메시지
                    await websocket.send(json.dumps({"log": "✅ [아이작심 PC] 대시보드와 완전히 연결되었습니다!"}))
                    
                    while True:
                        # 스레드 안전하게 전달받은 데이터를 기다림
                        payload = await self.queue.get()
                        await websocket.send(json.dumps(payload))
                        # 이제 터미널에 이게 찍힐 겁니다!
                        print(f"로그: [Socket] 웹으로 전송 완료 -> {payload['log'][:20]}...")
            except Exception as e:
                self.get_logger().error(f"Socket Error: {e}")
                await asyncio.sleep(2)

    def status_callback(self, msg):
        # ROS 스레드에서 비동기 스레드의 큐로 데이터를 '안전하게' 전달
        if self.loop and self.queue:
            payload = {"log": msg.data}
            print(f"로그: [Topic] 수신 및 큐 전달: {msg.data}")
            self.loop.call_soon_threadsafe(self.queue.put_nowait, payload)

    def yolo_text_callback(self, msg):
        if self.loop and self.queue:
            payload = {"log": msg.data}
            self.loop.call_soon_threadsafe(self.queue.put_nowait, payload)

def main(args=None):
    rclpy.init(args=args)
    node = RosToWebSender()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()