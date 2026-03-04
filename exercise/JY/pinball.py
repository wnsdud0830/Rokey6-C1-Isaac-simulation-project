import omni.isaac.core.utils.prims as prim_utils
from omni.isaac.core import World
from omni.isaac.core.objects import DynamicCuboid, DynamicSphere, FixedCuboid
import numpy as np

if World.instance() is None:
	world = World()
else:
	world = World.instance()

world.scene.clear()
world.scene.add_default_ground_plane()

thickness = 2.0
width = 1.5
height = 0.3

for i in range(4):
	if i % 2 == 0:
		x = 1
	else:
		x = -1
	y = 0
	z = 1*(i+1)
	
	FixedCuboid(
        prim_path=f"/World/Domino_{i}",
        name=f"domino_{i}",
        position=np.array([x, y, z]),
        scale=np.array([thickness, width, height]),
        color=np.array([1.0, 0.0, 0.0]),
        orientation=np.array([1.0, 0.0, -x/10, 0.0])
    )

ball = DynamicSphere(
    prim_path="/World/Ball",
    name="ball",
    position=np.array([-1, 0, 6]),
    radius=0.4,
    color=np.array([0.0, 1.0, 0.0]),
    mass=10.0
)

world.reset()
world.play()


