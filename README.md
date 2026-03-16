# UR10 Cleanroom 시뮬레이션 파이프라인 (Isaac Sim 5.0.0)

## 1. 프로젝트 개요
본 프로젝트는 **Isaac Sim 5.0.0** 환경에서 **Cleanroom 맵(Cleanroom.usd)** 위에 배치된 **UR10(2대) 로봇**을 이용해, 컨베이어로 이동하는 바이알(약병)을 **QR 판독 결과(A/B/C)**에 따라 분기 배치하는 시뮬레이션 파이프라인이다.

- **`ur10_final_run`**: Isaac Sim Script Editor에 붙여넣어 실행하는 메인 컨트롤 스크립트
- **`Cleanroom.usd`**: 시뮬레이션 맵(스테이지)
- **`qr_watcher.py`**: Isaac Sim이 저장한 이미지(`/tmp/isaac_qr_input.png`)를 외부(OpenCV)에서 QR 디코딩하고 결과(`/tmp/qr_result.json`)를 생성
- **`main.py`**: WebSocket 기반 로그 모니터(대시보드) 서버 (FastAPI)
- **`ros_to_web_thread.py`**: ROS2 토픽을 구독하여 대시보드 WebSocket으로 로그를 전달

> 제공된 파일 외의 구성(예: `/robot_status` 토픽 발행 주체, YOLO 노드 등)은 본 README에 단정하지 않았다.

---

## 2. 주요 기능

### 2.1 UR10 2대 연동 파이프라인
- “Giving 로봇”과 “Received 로봇” 두 대가 각각 역할을 분담하여 물체 이동/집기/배치를 수행한다.

### 2.2 QR 기반 바이알 타입 분기(A/B/C)
- Isaac Sim 내부 카메라 뷰포트 이미지를 파일로 저장한 뒤, 외부 프로세스가 QR을 판독해 **A/B/C** 중 하나를 반환한다.
- `qr_watcher.py`는 QR 텍스트가 `MEDICINE_A/B/C` 또는 `_A/_B/_C` 패턴일 때 **A/B/C**로 매핑한다.

### 2.3 외부 QR Watcher 연동 (파일 기반 IPC)
- `qr_watcher.py`는 `/tmp/isaac_qr_input.png` 파일이 생성/갱신되면 반복 판독을 수행하고, 결과를 `/tmp/qr_result.json`로 저장한다.
- QR 판독 안정화를 위해 최근 프레임을 누적하고, 일정 횟수 연속으로 동일 결과가 나오면 확정하는 로직이 포함되어 있다.

### 2.4 (옵션) ROS → Web 로그 모니터링
- `ros_to_web_thread.py`는 ROS2 토픽 **`/robot_status`**, **`/door_status`**, **`/yolo/detection_text`**를 구독하고, WebSocket 서버로 로그를 전송한다.
- 대시보드 서버(`main.py`)는 `/ws` WebSocket으로 들어온 메시지를 모든 접속자에게 브로드캐스트한다.

---

## 3. 시스템 설계

### 3.1 구성 요소 아키텍처

```mermaid
flowchart LR
  subgraph IsaacSim[Isaac Sim 5.0.0]
    A[Cleanroom.usd Stage]
    B[ur10_final_run\n(Script Editor)]
    A --> B
    B -->|capture viewport| IMG[/tmp/isaac_qr_input.png/]
    RES[/tmp/qr_result.json/]
    B <-->|poll result| RES
  end

  subgraph QR[External QR Watcher]
    QW[qr_watcher.py\n(OpenCV QRCodeDetector)]
    IMG --> QW
    QW -->|write JSON| RES
  end

  subgraph Web[Web Dashboard (Optional)]
    WS[main.py\nFastAPI + WebSocket :8000]
    BR[ros_to_web_thread.py\nROS2 Subscriber -> WS Sender]
    BR -->|ws://<server>:8000/ws| WS
  end
```

### 3.2 프로세스 플로우

```mermaid
flowchart TD
  S[시뮬레이션 시작\n(Isaac Sim Timeline Play)] --> R[ur10_final_run 실행]
  R --> C1[카메라 뷰포트 캡처\n/tmp/isaac_qr_input.png 저장]
  C1 --> Q1[qr_watcher.py가 파일 감지]
  Q1 --> Q2[OpenCV로 QR 디코딩]
  Q2 --> J[결과 JSON 저장\n/tmp/qr_result.json]
  J --> R2[ur10_final_run이 결과 Polling]
  R2 --> D{A/B/C 판정}
  D -->|A| PA[place_for_a로 분기]
  D -->|B| PB[place_for_b로 분기]
  D -->|C| PC[place_for_c로 분기]
```

---

## 4. 운영체제/실행 환경

### 4.1 Isaac Sim
- **Isaac Sim 5.0.0**
- `ur10_final_run`은 **Isaac Sim 내부 Script Editor**에서 실행한다.
- `Cleanroom.usd`는 Isaac Sim에서 **Stage(Open USD)**로 로드한다.

> Isaac Sim 실행 OS/드라이버/하드웨어 스펙은 제공 자료에 없어서 본 문서에 포함하지 않았다.

### 4.2 외부 Python 스크립트 (QR / Web / ROS)
- `qr_watcher.py`: OpenCV(`cv2`), NumPy 사용
- `main.py`: FastAPI + Uvicorn + WebSocket
- `ros_to_web_thread.py`: ROS2(rclpy) + websockets 라이브러리

---

## 5. 사용 자산/장비 목록

### 5.1 시뮬레이션 자산
- **맵(Stage)**: `Cleanroom.usd`
- **로봇**: UR10 2대(스크립트는 Giving/Received 로봇 루트 프림을 탐색하는 형태)
- **카메라**: QR 판독용 카메라 프림(스크립트가 후보 경로를 기반으로 탐색)
- **바이알 모델**: 타입 A/B/C에 대응하는 USD 자산 경로(스크립트 내 하드코딩 값)

### 5.2 외부 구성요소
- QR 판독용 외부 프로세스: `qr_watcher.py`
- (옵션) 로그 모니터링: `main.py`, `ros_to_web_thread.py`

---

## 6. 의존성 (requirements.txt)

본 프로젝트는 **Isaac Sim 내부 실행 코드**와 **외부 유틸리티(QR/Web/ROS)**로 나뉜다.

### 6.1 qr_watcher용 requirements (예: `requirements-qr.txt`)
`qr_watcher.py`는 `cv2`, `numpy`를 직접 import한다.

```txt
numpy
opencv-python
```

### 6.2 Web 대시보드 requirements (예: `requirements-web.txt`)
`main.py`는 `fastapi`, `uvicorn`을 직접 import한다.

```txt
fastapi
uvicorn
```

### 6.3 ROS → Web 브릿지 requirements (예: `requirements-ros-bridge.txt`)
`ros_to_web_thread.py`는 `websockets`를 직접 import하며, `rclpy/std_msgs`는 ROS2 설치에 포함되는 경우가 일반적이다.

```txt
websockets
```

> ROS2 관련(`rclpy`, `std_msgs`)은 pip가 아니라 ROS2 설치/환경 source로 준비하는 구성이 일반적이다.

---

## 7. 간단한 실행 순서

### 7.1 필수 실행 (QR 포함 파이프라인)
1. **Isaac Sim에서 `Cleanroom.usd` 로드**
2. Timeline을 **Play** 상태로 전환
3. 터미널 1: **QR watcher 실행**
   ```bash
   python3 qr_watcher.py
   ```
4. Isaac Sim Script Editor: **`ur10_final_run` 붙여넣기 → Run**

### 7.2 (옵션) 로그 대시보드 실행
1. 터미널 2: WebSocket 대시보드 서버 실행
   ```bash
   python3 main.py
   ```
   - 기본 포트: `8000`
2. 터미널 3: ROS → Web 브릿지 실행
   ```bash
   python3 ros_to_web_thread.py
   ```
   - 브릿지는 기본적으로 `ws://192.168.189.132:8000/ws`로 접속하도록 하드코딩되어 있다(환경에 맞게 수정 필요).

---

## 8. 설정/운영 시 주의사항

- **QR IPC 경로 일치**: Isaac Sim 스크립트와 `qr_watcher.py`는 동일한 경로(`/tmp/isaac_qr_input.png`, `/tmp/qr_result.json`)를 사용해야 한다.
- **네트워크 주소**: `ros_to_web_thread.py`의 WebSocket 서버 주소는 하드코딩되어 있으므로 실제 서버 IP/포트에 맞춰 갱신해야 한다.
- **토픽 존재**: `ros_to_web_thread.py`는 `/robot_status`, `/door_status`, `/yolo/detection_text` 구독을 전제로 한다. 해당 토픽 발행 노드는 제공 파일에 포함되지 않았다.

---

## 9. 파일 목록
- `ur10_final_run` (Isaac Sim Script Editor 실행)
- `Cleanroom.usd` (맵)
- `qr_watcher.py` (외부 QR 디코딩)
- `main.py` (WebSocket 로그 대시보드)
- `ros_to_web_thread.py` (ROS → Web 브릿지)
