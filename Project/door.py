import omni.usd
import omni.timeline
from isaacsim.sensors.physx import _range_sensor
import omni.physx as _physx


class DooMoDoorControl:
    def __init__(self):
        # =========================================================
        # 문별 설정
        # - sensors: 해당 문을 제어하는 센서들
        # - joints : 해당 문의 문짝 조인트들
        # - sign   : 열릴 때 방향 (+1 / -1)
        # =========================================================
        self.doors = [
            {
                "name": "door1",
                "sensors": [
                    "/Root/sensor/door1_front_sensor",
                    "/Root/sensor/door1_back_sensor",
                ],
                "joints": [
                    {
                        "path": "/Root/door_joint/left_door_Joint",
                        "sign": -1,
                    },
                    {
                        "path": "/Root/door_joint/right_door_Joint",
                        "sign": 1,
                    },
                ],
            },
            {
                "name": "door2",
                "sensors": [
                    "/Root/sensor/door2_front_sensor",
                    "/Root/sensor/door2_back_sensor",
                ],
                "joints": [
                    {
                        "path": "/Root/door_joint/left_door_Joint1",
                        "sign": -1,
                    },
                    {
                        "path": "/Root/door_joint/right_door_Joint1",
                        "sign": 1,
                    },
                ],
            },
        ]

        self.attr_name = "drive:linear:physics:targetPosition"

        self.open_value = 0.5

        self.close_value = 0.0

        self._ls = _range_sensor.acquire_lightbeam_sensor_interface()
        self._timeline = omni.timeline.get_timeline_interface()
        self._physx_subscription = _physx.get_physx_interface().subscribe_physics_step_events(self._on_update)

        # 상태 변화 로그용
        self._prev_states = {door["name"]: False for door in self.doors}

        print("DOOMO_LOG | System initialized. Monitoring grouped door sensors...")

    def _sensor_hit(self, sensor_path):
        try:
            beam_hit = self._ls.get_beam_hit_data(sensor_path)
            return beam_hit is not None and any(beam_hit.astype(bool))
        except Exception as e:
            print(f"DOOMO_LOG | SENSOR_READ_ERROR @ {sensor_path}: {str(e)}")
            return False

    def _on_update(self, dt):
        if not self._timeline.is_playing():
            return

        stage = omni.usd.get_context().get_stage()

        try:
            for door in self.doors:
                door_name = door["name"]

                # 해당 문의 센서 2개 중 하나라도 hit면 그 문만 열기
                is_hit = any(self._sensor_hit(sensor_path) for sensor_path in door["sensors"])

                target_val = self.open_value if is_hit else self.close_value

                for joint in door["joints"]:
                    joint_path = joint["path"]
                    sign = joint["sign"]

                    prim = stage.GetPrimAtPath(joint_path)
                    if not prim.IsValid():
                        print(f"DOOMO_LOG | INVALID_PRIM: {joint_path}")   # 수정 필요!! 경로 확인
                        continue

                    attr = prim.GetAttribute(self.attr_name)
                    if not attr.IsValid():
                        print(f"DOOMO_LOG | INVALID_ATTR: {self.attr_name} @ {joint_path}")
                        continue

                    attr.Set(sign * target_val)

                # 상태 변화가 있을 때만 로그
                if self._prev_states[door_name] != is_hit:
                    if is_hit:
                        print(f"DOOMO_LOG | {door_name}: SENSOR_HIT TRUE - Opening")
                    else:
                        print(f"DOOMO_LOG | {door_name}: SENSOR_HIT FALSE - Closing")
                    self._prev_states[door_name] = is_hit

        except Exception as e:
            print(f"DOOMO_LOG | RUNTIME_ERROR: {str(e)}")


# Create instance
door_controller = DooMoDoorControl()