import omni.isaac.core.utils.prims as prim_utils
from omni.isaac.core import World
from omni.isaac.core.objects import DynamicCuboid, DynamicSphere
import numpy as np
from scipy.spatial.transform import Rotation as R

world = World()
world.scene.clear()
world.scene.add_default_ground_plane()

domino_count = 20
radius = 2.0
height = 0.6
thickness = 0.1
width = 0.3

for i in range(domino_count):
	angle = (i / (domino_count - 1)) * np.pi
	
	x = radius * np.cos(angle)
	y = radius * np.sin(angle)
	z = height / 2.0
	yaw = angle + np.pi / 2
	
	prim_path = f"/World/Domino_{i}"

	domino = DynamicCuboid(
		prim_path = prim_path,
		position = np.array([x, y, z]),
		scale = np.array([thickness, width, height]),
		color = np.array([1.0, 0.0, 0.0])
	)
	
	r = R.from_euler('z', yaw, degrees=False)
	quat = r.as_quat()
	isaac_quat = np.array([quat[3], quat[0], quat[1], quat[2]])
	
	domino.set_world_pose(orientation=isaac_quat)
	
ball = DynamicSphere(
	prim_path = "/World/Trigger_Ball",
	position = np.array([radius , -0.5, height]),
	radius = 0.15,
	color = np.array([0.0, 1.0, 0.0]),
	mass = 5.0
)

ball.set_linear_velocity(np.array([0.0, 2.0, 0.0]))
