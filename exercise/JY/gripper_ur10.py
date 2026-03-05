import numpy as np
import sys
import carb

from isaacsim.examples.interactive.base_sample import BaseSample

from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.storage.native import get_assets_root_path
from isaacsim.robot.manipulators.grippers import SurfaceGripper
from isaacsim.robot.manipulators import SingleManipulator
from isaacsim.core.api.objects import DynamicCuboid

import isaacsim.robot_motion.motion_generation as mg
from isaacsim.core.utils.rotations import euler_angles_to_quat
from isaacsim.core.prims import SingleArticulation


class RMPFlowController(mg.MotionPolicyController):

    def __init__(
        self,
        name: str,
        robot_articulation: SingleArticulation,
        physics_dt: float = 1.0 / 60.0,
        attach_gripper: bool = False,
    ) -> None:

        if attach_gripper:
            self.rmp_flow_config = mg.interface_config_loader.load_supported_motion_policy_config(
                "UR10", "RMPflowSuction"
            )
        else:
            self.rmp_flow_config = mg.interface_config_loader.load_supported_motion_policy_config("UR10", "RMPflow")
        self.rmp_flow = mg.lula.motion_policies.RmpFlow(**self.rmp_flow_config)

        self.articulation_rmp = mg.ArticulationMotionPolicy(robot_articulation, self.rmp_flow, physics_dt)

        mg.MotionPolicyController.__init__(self, name=name, articulation_motion_policy=self.articulation_rmp)
        (
            self._default_position,
            self._default_orientation,
        ) = self._articulation_motion_policy._robot_articulation.get_world_pose()
        self._motion_policy.set_robot_base_pose(
            robot_position=self._default_position, robot_orientation=self._default_orientation
        )
        return

    def reset(self):
        mg.MotionPolicyController.reset(self)
        self._motion_policy.set_robot_base_pose(
            robot_position=self._default_position, robot_orientation=self._default_orientation
        )


class Gripper_UR10(BaseSample):
    def __init__(self) -> None:
        super().__init__()

        self.BROWN = np.array([0.5, 0.2, 0.1])

        # 3개 큐브 초기 위치(원하는 대로 바꿔도 됨)
        self._cube_positions = [
            np.array([0.5,  0.00, 0.025]),
            np.array([0.5,  0.12, 0.025]),
            np.array([0.5, -0.12, 0.025]),
        ]

        self.task_phase = 1
        return

    def setup_scene(self):
        world = self.get_world()
        world.scene.add_default_ground_plane()

        assets_root_path = get_assets_root_path()
        if assets_root_path is None:
            carb.log_error("Could not find Isaac Sim assets folder")
            simulation_app.close()
            sys.exit()

        asset_path = assets_root_path + "/Isaac/Robots/UniversalRobots/ur10/ur10.usd"
        robot = add_reference_to_stage(usd_path=asset_path, prim_path="/World/UR10")
        robot.GetVariantSet("Gripper").SetVariantSelection("Short_Suction")

        gripper = SurfaceGripper(
            end_effector_prim_path="/World/UR10/ee_link",
            surface_gripper_path="/World/UR10/ee_link/SurfaceGripper"
        )

        ur10 = world.scene.add(
            SingleManipulator(
                prim_path="/World/UR10",
                name="my_ur10",
                end_effector_prim_path="/World/UR10/ee_link",
                gripper=gripper
            )
        )

        ur10.set_joints_default_state(
            positions=np.array([-np.pi / 2, -np.pi / 2, -np.pi / 2, -np.pi / 2, np.pi / 2, 0])
        )

        # ---- 동일 큐브 3개 생성 ----
        for i, p in enumerate(self._cube_positions):
            world.scene.add(
                DynamicCuboid(
                    prim_path=f"/World/BrownCube_{i}",
                    name=f"brown_cube_{i}",
                    position=p,
                    scale=np.array([0.05, 0.05, 0.05]),
                    color=self.BROWN
                )
            )

        return

    def move_point(self, goal_position: np.ndarray, end_effector_orientation: np.ndarray=np.array([0, np.pi/2, 0])) -> bool:
        end_effector_orientation = euler_angles_to_quat(end_effector_orientation)
        target_joint_positions = self.cspace_controller.forward(
            target_end_effector_position=goal_position,
            target_end_effector_orientation=end_effector_orientation
        )
        self.robots.apply_action(target_joint_positions)
        current_joint_positions = self.robots.get_joint_positions()
        is_reached = np.all(np.abs(current_joint_positions[:7] - target_joint_positions.joint_positions) < 0.001)
        return is_reached

    async def setup_post_load(self):
        self._world = self.get_world()
        self.robots = self._world.scene.get_object("my_ur10")

        # 큐브 3개 핸들
        self._cubes = [self._world.scene.get_object(f"brown_cube_{i}") for i in range(3)]

        self.cspace_controller = RMPFlowController(
            name="my_ur10_cspace_controller",
            robot_articulation=self.robots,
            attach_gripper=True
        )

        # 기존 변수 유지(여기서 첫 번째 포인트를 "적층 위치 상공"으로 사용)
        # => 적층 XY는 _goal_points[0]의 x,y 를 사용, z는 상공 높이로 사용
        self._goal_points = [
            np.array([-1.0, 0.00, 0.30]),  # [STACK_X, STACK_Y, STACK_ABOVE_Z]
            np.array([0.30, -0.30, 0.30])
        ]

        self.task_phase = 1
        self._goal_reached = False

        # ---- 3개 처리 상태 ----
        self._placed_count = 0
        self._active_cube_idx = 0
        self._done_flags = [False, False, False]

        # phase 내부 sub-step (바깥 phase 구조는 그대로)
        self._phase3_sub = 0  # 0: pick 후 상공 lift, 1: stack 상공 이동, 2: stack 높이로 하강
        self._phase4_sub = 0  # 0: open, 1: stack 상공으로 후퇴

        self._world.add_physics_callback("sim_step", callback_fn=self.physics_step)
        await self._world.play_async()
        return

    def _select_next_cube(self):
        """남은 큐브 중 다음 큐브 선택(순서 상관없으면 그냥 남은 것 아무거나)."""
        for i in range(3):
            if not self._done_flags[i]:
                self._active_cube_idx = i
                return True
        return False

    def physics_step(self, step_size):
        # 전부 적층 완료하면 아무것도 안 함
        if self._placed_count >= 3:
            return

        # 현재 타겟 큐브
        cube = self._cubes[self._active_cube_idx]

        # 적층 타겟(특정 좌표): _goal_points[0]의 x,y 사용
        stack_xy = self._goal_points[0][:2]
        stack_above_z = float(self._goal_points[0][2])

        # 큐브 스케일 0.05 기준: 센터 z = 0.025 + n*0.05
        place_center_z = 0.025 + self._placed_count * 0.05
        # 릴리즈는 살짝 위에서(기존 픽 접근 z=0.045에 맞춰 +0.02)
        place_release_z = place_center_z + 0.02

        if self.task_phase == 1:
            # 큐브 위치로 접근(픽업 높이는 기존처럼 0.045로)
            cube_position, _ = cube.get_world_pose()
            cube_position[2] = 0.045

            self._goal_reached = self.move_point(cube_position)
            if self._goal_reached:
                self.cspace_controller.reset()
                self.task_phase = 2

        elif self.task_phase == 2:
            # 집기(흡착)
            self.robots.gripper.close()
            self._phase3_sub = 0
            self.task_phase = 3

        elif self.task_phase == 3:
            # (sub0) 픽업 후 상공으로 lift
            if self._phase3_sub == 0:
                cube_position, _ = cube.get_world_pose()
                cube_position[2] = 0.40  # 기존 코드 lift 높이 유지

                self._goal_reached = self.move_point(cube_position)
                if self._goal_reached:
                    self.cspace_controller.reset()
                    self._phase3_sub = 1

            # (sub1) 적층 위치 상공으로 이동
            elif self._phase3_sub == 1:
                above_stack = np.array([stack_xy[0], stack_xy[1], stack_above_z], dtype=float)

                self._goal_reached = self.move_point(above_stack)
                if self._goal_reached:
                    self.cspace_controller.reset()
                    self._phase3_sub = 2

            # (sub2) 적층 높이로 하강(릴리즈 높이)
            elif self._phase3_sub == 2:
                release_pos = np.array([stack_xy[0], stack_xy[1], place_release_z], dtype=float)

                self._goal_reached = self.move_point(release_pos)
                if self._goal_reached:
                    self.cspace_controller.reset()
                    self._phase4_sub = 0
                    self.task_phase = 4

        elif self.task_phase == 4:
            # (sub0) 놓기
            if self._phase4_sub == 0:
                self.robots.gripper.open()
                self._phase4_sub = 1

            # (sub1) 적층 위치 상공으로 후퇴
            elif self._phase4_sub == 1:
                above_stack = np.array([stack_xy[0], stack_xy[1], stack_above_z], dtype=float)

                self._goal_reached = self.move_point(above_stack)
                if self._goal_reached:
                    self.cspace_controller.reset()
                    self.task_phase = 5

        elif self.task_phase == 5:
            # 다음 큐브로 반복(구조 유지 차원에서 phase5를 “루프 갱신”으로 사용)
            self._done_flags[self._active_cube_idx] = True
            self._placed_count += 1

            if self._placed_count >= 3:
                self.task_phase = 999
                return

            # 다음 큐브 선택(순서 상관없음)
            if not self._select_next_cube():
                self.task_phase = 999
                return

            self.task_phase = 1

        return