#usda 1.0

def "Item_00"
{
    def OmniGraphNode "script_node" (
        prepend apiSchemas = ["NodeGraphNodeAPI"]
    )
    {
        custom double inputs:deltaSimulationTime
        prepend double inputs:deltaSimulationTime.connect = </Root/Sensor_ActionGraph/on_physics_step.outputs:deltaSimulationTime>
        custom uint inputs:execIn (
            customData = {
                bool isExecution = 1
            }
        )
        prepend uint inputs:execIn.connect = </Root/Sensor_ActionGraph/on_physics_step.outputs:step>
        custom string inputs:script = '''import omni.usd
from isaacsim.sensors.physx import _range_sensor

DOORS = [
    {
        "name": "Cleanroom_Door",
        "sensors": [
            "/Root/sensor/door1_front_sensor",
            "/Root/sensor/door1_back_sensor",
        ],
        "joints": [
            {"path": "/Root/door_joint/left_door_Joint", "sign": -1},
            {"path": "/Root/door_joint/right_door_Joint", "sign": 1},
        ],
    },
    {
        "name": "Packageroom_Door",
        "sensors": [
            "/Root/sensor/door2_front_sensor",
            "/Root/sensor/door2_back_sensor",
        ],
        "joints": [
            {"path": "/Root/door_joint/left_door_Joint1", "sign": -1},
            {"path": "/Root/door_joint/right_door_Joint1", "sign": 1},
        ],
    },
]

ATTR_NAME = "drive:linear:physics:targetPosition"
OPEN_VALUE = 0.5
CLOSE_VALUE = 0.0
CLOSE_DELAY = 1.0

STATE_IDLE = 0
STATE_WAIT_ENTRY_CLEAR = 1
STATE_WAIT_OPPOSITE = 2
STATE_WAIT_CLOSE = 3


def _emit_event(state, text: str):
    print(text)
    state.pending_message = text


def setup(db):
    state = db.internal_state
    state.lightbeam = _range_sensor.acquire_lightbeam_sensor_interface()

    state.door_open_states = {door["name"]: False for door in DOORS}
    state.phase = {door["name"]: STATE_IDLE for door in DOORS}
    state.entry_sensor = {door["name"]: None for door in DOORS}
    state.clear_times = {door["name"]: 0.0 for door in DOORS}
    state.prev_sensor_hits = {
        door["name"]: {sensor_path: False for sensor_path in door["sensors"]}
        for door in DOORS
    }

    # ROS2 Publisher 예열용: 3 ticks
    state.prime_ticks_left = 3
    state.pending_message = ""

    print("VIRUS_CQC_LOG | Door controller initialized.")


def cleanup(db):
    print("VIRUS_CQC_LOG | Door controller cleaned up.")


def _sensor_hit(lightbeam_interface, sensor_path):
    try:
        beam_hit = lightbeam_interface.get_beam_hit_data(sensor_path)
        return beam_hit is not None and any(beam_hit.astype(bool))
    except Exception as e:
        print(f"VIRUS_CQC_LOG | SENSOR_READ_ERROR @ {sensor_path}: {str(e)}")
        return False


def _set_door_target(stage, door, target_value):
    for joint in door["joints"]:
        joint_path = joint["path"]
        sign = joint["sign"]

        prim = stage.GetPrimAtPath(joint_path)
        if not prim.IsValid():
            print(f"VIRUS_CQC_LOG | INVALID_PRIM: {joint_path}")
            continue

        attr = prim.GetAttribute(ATTR_NAME)
        if not attr.IsValid():
            print(f"VIRUS_CQC_LOG | INVALID_ATTR: {ATTR_NAME} @ {joint_path}")
            continue

        attr.Set(sign * target_value)


def _reset_door_state(state, door_name):
    state.phase[door_name] = STATE_IDLE
    state.entry_sensor[door_name] = None
    state.clear_times[door_name] = 0.0


def compute(db):
    state = db.internal_state
    dt = db.inputs.deltaSimulationTime
    stage = omni.usd.get_context().get_stage()

    # 기본 출력
    db.outputs.logMessage = ""
    db.outputs.shouldPublish = False

    # 이번 프레임 이벤트 메시지 초기화
    state.pending_message = ""

    try:
        for door in DOORS:
            door_name = door["name"]
            sensor_paths = door["sensors"]

            sensor_hits = {}
            rising_sensors = []

            for sensor_path in sensor_paths:
                hit = _sensor_hit(state.lightbeam, sensor_path)
                sensor_hits[sensor_path] = hit

                prev_hit = state.prev_sensor_hits[door_name][sensor_path]
                if hit and not prev_hit:
                    rising_sensors.append(sensor_path)

            front_sensor = sensor_paths[0]
            back_sensor = sensor_paths[1]
            phase = state.phase[door_name]

            if phase == STATE_IDLE and len(rising_sensors) > 0:
                entry_sensor = rising_sensors[0]
                state.entry_sensor[door_name] = entry_sensor
                state.phase[door_name] = STATE_WAIT_ENTRY_CLEAR
                state.clear_times[door_name] = 0.0

                if not state.door_open_states[door_name]:
                    state.door_open_states[door_name] = True
                    _emit_event(state, f"VIRUS_CQC_LOG | {door_name}: OPEN")

            elif phase == STATE_WAIT_ENTRY_CLEAR:
                entry_sensor = state.entry_sensor[door_name]
                if entry_sensor is not None and not sensor_hits[entry_sensor]:
                    state.phase[door_name] = STATE_WAIT_OPPOSITE

            elif phase == STATE_WAIT_OPPOSITE:
                entry_sensor = state.entry_sensor[door_name]
                opposite_sensor = back_sensor if entry_sensor == front_sensor else front_sensor

                if opposite_sensor in rising_sensors:
                    state.phase[door_name] = STATE_WAIT_CLOSE
                    state.clear_times[door_name] = 0.0

            elif phase == STATE_WAIT_CLOSE:
                any_hit = any(sensor_hits.values())

                if any_hit:
                    state.clear_times[door_name] = 0.0
                else:
                    state.clear_times[door_name] += dt
                    if state.clear_times[door_name] >= CLOSE_DELAY:
                        if state.door_open_states[door_name]:
                            state.door_open_states[door_name] = False
                            _emit_event(state, f"VIRUS_CQC_LOG | {door_name}: CLOSE")
                        _reset_door_state(state, door_name)

            target_value = OPEN_VALUE if state.door_open_states[door_name] else CLOSE_VALUE
            _set_door_target(stage, door, target_value)

            for sensor_path in sensor_paths:
                state.prev_sensor_hits[door_name][sensor_path] = sensor_hits[sensor_path]

        # ---- 여기서만 publish 출력 결정 ----

        # 실제 이벤트가 생긴 프레임
        if state.pending_message:
            db.outputs.logMessage = state.pending_message
            db.outputs.shouldPublish = True

        # 퍼블리셔 예열
        elif state.prime_ticks_left > 0:
            db.outputs.logMessage = "Door System is Ready!"
            db.outputs.shouldPublish = True
            state.prime_ticks_left -= 1

        return True

    except Exception as e:
        print(f"VIRUS_CQC_LOG | RUNTIME_ERROR: {str(e)}")
        return False'''
        custom token inputs:scriptPath
        custom bool inputs:usePath
        token node:type = "omni.graph.scriptnode.ScriptNode"
        int node:typeVersion = 2
        custom uint outputs:execOut (
            customData = {
                bool isExecution = 1
            }
        )
        custom string outputs:logMessage
        custom bool outputs:shouldPublish
        custom bool state:omni_initialized
        uniform token ui:nodegraph:node:expansionState = "open"
        uniform float2 ui:nodegraph:node:pos = (300.32574, 152.33685)
    }
}

