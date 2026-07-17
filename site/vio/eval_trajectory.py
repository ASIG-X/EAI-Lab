import argparse
import os
from pathlib import Path

import numpy as np
import rclpy
import rclpy.time
from matplotlib import pyplot as plt
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_types_from_msg, get_typestore

from trajectory_aligner import TrajectoryAligner

parser = argparse.ArgumentParser(description="Evaluate trajectory estimation")
parser.add_argument("--bagpath", type=str, required=True, help="Path to the bag file")
parser.add_argument("--save-path", type=str, required=True, help="Directory to save trajectory results")
parser.add_argument("--euroc", action="store_true", help="Use Euroc dataset")
parser.add_argument("--no-loop-closure", action="store_true", help="Disable loop closure")
group = parser.add_mutually_exclusive_group()
group.add_argument("--rigid-body-index", type=int, default=None, help="Index of the rigid body to use as ground truth")
group.add_argument("--rigid-body-name", type=str, default=None, help="Name of the rigid body to use as ground truth")
args = parser.parse_args()

# path to the bag folder
if not os.path.isdir(args.bagpath):
    raise RuntimeError(f"Invalid bag path: {args.bagpath}")
BAGPATH = Path(args.bagpath)

# create save directory if it doesn't exist
SAVE_PATH = Path(args.save_path)
os.makedirs(SAVE_PATH, exist_ok=True)

MARKER_MSG = """
int8 USE_NAME=0
int8 USE_INDEX=1
int8 USE_BOTH=2

int8 id_type
int32 marker_index
string marker_name
geometry_msgs/Point translation
"""

RIGID_BODY_MSG = """
string rigid_body_name
Marker[] markers
geometry_msgs/Pose pose
"""

RIGID_BODIES_MSG = """
std_msgs/Header header
uint32 frame_number
mocap4r2_msgs/RigidBody[] rigidbodies
"""

# register message types
typestore = get_typestore(Stores.ROS2_HUMBLE)
typestore.register(get_types_from_msg(MARKER_MSG, "mocap4r2_msgs/msg/Marker"))
typestore.register(get_types_from_msg(RIGID_BODY_MSG, "mocap4r2_msgs/msg/RigidBody"))
typestore.register(get_types_from_msg(RIGID_BODIES_MSG, "mocap4r2_msgs/msg/RigidBodies"))

vins_traj_topic = "/pose_graph/pose_graph_path"
if args.no_loop_closure:
    vins_traj_topic = "/vins_estimator/path"
gt_traj_topic = "/rigid_bodies"
if args.euroc:
    gt_traj_topic = "/leica/position"

# read estimated trajectory
timestamps = None
positions = None
quaternions = None
with AnyReader([BAGPATH], default_typestore=typestore) as reader:
    connections = [x for x in reader.connections if x.topic == vins_traj_topic]
    connection, timestamp, rawdata = list(reader.messages(connections=connections))[-1]
    msg = reader.deserialize(rawdata, connection.msgtype)
    timestamps = []
    positions = []
    quaternions = []
    for pose_stamped in msg.poses:
        # read tmiestamp
        timestamp = rclpy.time.Time(
            seconds=pose_stamped.header.stamp.sec, nanoseconds=pose_stamped.header.stamp.nanosec
        ).nanoseconds
        timestamps.append(timestamp)
        # read pose
        pose = pose_stamped.pose
        positions.append(
            [
                pose.position.x,
                pose.position.y,
                pose.position.z,
            ]
        )
        quaternions.append(
            [
                pose.orientation.x,
                pose.orientation.y,
                pose.orientation.z,
                pose.orientation.w,
            ]
        )


est_traj_ts = np.array(timestamps).astype(np.float64)
est_traj_ts /= 1e9
est_traj_pos = np.array(positions)
est_traj_quat = np.array(quaternions)


# read camera tracking (ground truth) trajectory
timestamps = []
positions = []
quaternions = []
with AnyReader([BAGPATH], default_typestore=typestore) as reader:
    connections = [x for x in reader.connections if x.topic == gt_traj_topic]
    for connection, timestamp, rawdata in reader.messages(connections=connections):
        msg = reader.deserialize(rawdata, connection.msgtype)
        # read tmiestamp
        timestamp = rclpy.time.Time(seconds=msg.header.stamp.sec, nanoseconds=msg.header.stamp.nanosec).nanoseconds
        timestamps.append(timestamp)
        if args.euroc:
            positions.append((msg.point.x, msg.point.y, msg.point.z))
            quaternions.append((0, 0, 0, 1))
        else:
            # select rigid body by name or index
            if args.rigid_body_name is not None:
                rb = next((r for r in msg.rigidbodies if r.rigid_body_name == args.rigid_body_name), None)
                if rb is None:
                    timestamps.pop()
                    continue
            else:
                idx = args.rigid_body_index if args.rigid_body_index is not None else 1
                rb = msg.rigidbodies[idx]
            positions.append(
                (
                    rb.pose.position.x,
                    rb.pose.position.y,
                    rb.pose.position.z,
                )
            )
            quaternions.append(
                (
                    rb.pose.orientation.x,
                    rb.pose.orientation.y,
                    rb.pose.orientation.z,
                    rb.pose.orientation.w,
                )
            )
        if any([np.isnan(x) for x in positions[-1]]) or any([np.isnan(x) for x in quaternions[-1]]):
            timestamps.pop()
            positions.pop()
            quaternions.pop()

gt_traj_ts = np.array(timestamps).astype(np.float64)
gt_traj_ts /= 1e9
gt_traj_pos = np.array(positions)
gt_traj_quat = np.array(quaternions)


# keep poses only within common time span of both trajectories
time_0 = max(est_traj_ts[0], gt_traj_ts[0])
time_1 = min(est_traj_ts[-1], gt_traj_ts[-1])

est_mask = (est_traj_ts >= time_0) & (est_traj_ts <= time_1)
gt_mask = (gt_traj_ts >= time_0) & (gt_traj_ts <= time_1)

est_traj_ts = est_traj_ts[est_mask]
est_traj_pos = est_traj_pos[est_mask]
est_traj_quat = est_traj_quat[est_mask]

gt_traj_ts = gt_traj_ts[gt_mask]
gt_traj_pos = gt_traj_pos[gt_mask]
gt_traj_quat = gt_traj_quat[gt_mask]

est_traj_ts -= time_0
gt_traj_ts -= time_0

print(f"timestamps of ground truth trajectory poses:  {gt_traj_ts.shape}")
print(f"positions of ground truth trajectory poses:   {gt_traj_pos.shape}")
print(f"quaternions of ground truth trajectory poses: {gt_traj_quat.shape}")

print(f"timestamps of estimated trajectory poses:     {est_traj_ts.shape}")
print(f"positions of estimated trajectory poses:      {est_traj_pos.shape}")
print(f"quaternions of estimated trajectory poses:    {est_traj_quat.shape}")


# align ground truth trajectory to estimated trajectory
traj_aligner = TrajectoryAligner(est_traj_ts, est_traj_pos, est_traj_quat, gt_traj_ts, gt_traj_pos, gt_traj_quat)
align_gt_traj_pos = traj_aligner.align()
print(f"aligned trajectory poses:                     {align_gt_traj_pos.shape}")


# plot trajectories
fig = plt.figure()
ax = plt.axes(projection="3d")
ax.plot3D(align_gt_traj_pos[:, 0], align_gt_traj_pos[:, 1], align_gt_traj_pos[:, 2], label="ground truth")
ax.plot3D(est_traj_pos[:, 0], est_traj_pos[:, 1], est_traj_pos[:, 2], label="estimation")
ax.legend()
plt.show()


print(f"saving trajectories to tum format in {SAVE_PATH}...")
with open(SAVE_PATH / "est_traj.txt", "w") as f:
    for i in range(est_traj_pos.shape[0]):
        # we do not evaluate rotations
        f.write(f"{est_traj_ts[i]} {est_traj_pos[i][0]} {est_traj_pos[i][1]} {est_traj_pos[i][2]} 0 0 0 1\n")
with open(SAVE_PATH / "gt_traj.txt", "w") as f:
    for i in range(align_gt_traj_pos.shape[0]):
        f.write(
            f"{est_traj_ts[i]} {align_gt_traj_pos[i][0]} {align_gt_traj_pos[i][1]} {align_gt_traj_pos[i][2]} 0 0 0 1\n"
        )
