import numpy as np
import scipy.interpolate as interp
import scipy.optimize as opt
import sophuspy as sp


def interpolate_trajectory(source_ts, source_data, target_ts):
    """
    Interpolate trajectory data to new timestamps.
    """
    if source_data.shape[0] == 0 or target_ts.shape[0] == 0:
        return np.array([])

    interpolator = interp.interp1d(source_ts, source_data, axis=0, bounds_error=False, fill_value="extrapolate")
    return interpolator(target_ts)


def traj_pos_align_error(twist, ref_traj_ts, ref_traj_pos, est_traj_ts, est_traj_pos):
    T = sp.SE3.exp(twist)

    # First transform the reference positions
    ref_traj_pos_transformed = np.zeros_like(ref_traj_pos)
    for i in range(ref_traj_pos.shape[0]):
        ref_traj_pos_transformed[i] = T * ref_traj_pos[i]

    # Then interpolate to estimated timestamps
    ref_traj_pos_aligned = interpolate_trajectory(ref_traj_ts, ref_traj_pos_transformed, est_traj_ts)

    return np.linalg.norm(est_traj_pos - ref_traj_pos_aligned)


class TrajectoryAligner:
    def __init__(self, est_traj_ts, est_traj_pos, est_traj_quat, gt_traj_ts, gt_traj_pos, gt_traj_quat):
        self.est_traj_ts = est_traj_ts
        self.est_traj_pos = est_traj_pos
        self.est_traj_quat = est_traj_quat
        self.gt_traj_ts = gt_traj_ts
        self.gt_traj_pos = gt_traj_pos
        self.gt_traj_quat = gt_traj_quat

    def align(self):
        initial_guess = np.zeros(6)
        # Optimize the twist to minimize position alignment error
        # Now aligns ground truth to estimated trajectory
        result = opt.minimize(
            lambda twist: traj_pos_align_error(
                twist, self.gt_traj_ts, self.gt_traj_pos, self.est_traj_ts, self.est_traj_pos
            ),
            initial_guess,
            method="BFGS",
        )

        # Get the optimal twist and transformation
        optimal_twist = result.x
        T_align = sp.SE3.exp(optimal_twist)

        # Apply transformation to gt_traj_pos in place
        for i in range(self.gt_traj_pos.shape[0]):
            self.gt_traj_pos[i] = T_align * self.gt_traj_pos[i]

        # Interpolate the aligned ground truth to estimated timestamps
        aligned_gt_at_est_ts = interpolate_trajectory(self.gt_traj_ts, self.gt_traj_pos, self.est_traj_ts)

        # Return the interpolated trajectory
        return aligned_gt_at_est_ts
