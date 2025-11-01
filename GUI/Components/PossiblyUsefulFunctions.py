"""
Filename: PossiblyUsefulFunctions.py
Author: Nikola Markoski
Description: This file contains functions that could be handy in the future
"""

def generate_adjacency_matrix(self, positions, tx_power_dbm=20.0, tx_gain_db=0.0, rx_gain_db=0.0, freq_hz=2.4e9, extra_loss_db=0.0, blocked_loss_db=999.0, min_distance=1e-3):
        c = 3e8

        if not self.satellites:
            return None, None

        # Build positions array and keys
        keys = list(positions)
        P = np.array(list(positions.values()), dtype=float)
        N = P.shape[0]
        if N == 0:
            return np.array([]), np.array([[]])

        # Pairwise difference vectors and distances
        D = P[None, :, :] - P[:, None, :]           # shape (N,N,3)
        dist = np.linalg.norm(D, axis=2)            # shape (N,N)
        # clamp small distances to avoid log10(0)
        dist_clamped = np.maximum(dist, min_distance)

        # Quadratic coefficients for intersection with radius ERAD/1000
        a = np.sum(D * D, axis=2)
        b = 2 * np.sum(P[:, None, :] * D, axis=2)
        c_coef = np.sum(P[:, None, :] * P[:, None, :], axis=2) - ERAD/1000

        # Discriminant and safe t calculation
        disc = b**2 - 4 * a * c_coef
        t1 = np.full_like(disc, np.inf)
        t2 = np.full_like(disc, np.inf)
        valid = (disc >= 0) & (a != 0)
        sqrt_disc = np.zeros_like(disc)
        sqrt_disc[valid] = np.sqrt(disc[valid])
        t1[valid] = (-b[valid] - sqrt_disc[valid]) / (2 * a[valid])
        t2[valid] = (-b[valid] + sqrt_disc[valid]) / (2 * a[valid])

        # Intersection occurs if t1 or t2 in [0, 1]
        intersects = (valid & ( ((t1 >= 0) & (t1 <= 1)) | ((t2 >= 0) & (t2 <= 1)) ))

        # LOS matrix: True if blocked (intersection), False if unobstructed
        blocked = intersects
        adj_matrix = (~blocked).astype(int)
        np.fill_diagonal(adj_matrix, 0)

        # --- Propagation model: Free-Space Path Loss (FSPL) ---
        # FSPL_dB = 20*log10(d) + 20*log10(f) - 147.56   (d in meters, f in Hz)
        # Received dBm = tx_power_dbm + tx_gain_db + rx_gain_db - FSPL_dB - extra_loss_db

        # compute FSPL (dB)
        with np.errstate(divide='ignore'):
            fspl_db = 20.0 * np.log10(dist_clamped) + 20.0 * np.log10(freq_hz) - 147.56

        # Received power (dBm) assuming symmetric tx/rx for simplicity
        rx_power_dbm = tx_power_dbm + tx_gain_db + rx_gain_db - fspl_db - extra_loss_db

        # For blocked links, apply very large attenuation (set to extremely low received power)
        rx_power_dbm_blocked = rx_power_dbm - blocked_loss_db

        # Combine: where blocked True -> blocked value, else normal rx_power
        strength_dbm = np.where(blocked, rx_power_dbm_blocked, rx_power_dbm)

        # Optionally set diagonal entries to a sentinel (self-link)
        strength_dbm[np.diag_indices(N)] = -np.inf

        return adj_matrix, strength_dbm

def build_adjacency_matrix(space_objects, earth_radius_km):
    """
    Build a square adjacency matrix for all space objects.
    
    Parameters
    ----------
    space_objects : dict
        Keys are object names/IDs, values are objects with:
            - position : np.array([x, y, z]) in km
            - type : 'satellite' or 'groundstation'
    earth_radius_km : float
        Radius of the Earth in km
    
    Returns
    -------
    adj_matrix : np.ndarray
        Boolean adjacency matrix (N x N)
        True = visible (LOS exists), False = blocked
    keys : list
        List of object keys corresponding to the adjacency matrix rows/columns
    """
    keys = list(space_objects.keys())
    N = len(keys)
    positions = np.array([space_objects[k].position for k in keys], dtype=float)
    is_satellite = np.array([space_objects[k].type == 'satellite' for k in keys], dtype=bool)
 
    adj_matrix = np.zeros((N, N), dtype=bool)
 
    # Compute pairwise vectors and distances
    vecs = positions[None, :, :] - positions[:, None, :]  # shape: (N, N, 3)
    dists_sq = np.sum(vecs**2, axis=2)
 
    # Avoid self-connections
    np.fill_diagonal(dists_sq, np.inf)
 
    # Determine which pairs need LOS computation
    compute_mask = np.logical_or(is_satellite[:, None], is_satellite[None, :])
 
    # Unit vectors for ray direction
    directions = np.zeros_like(vecs)
    nonzero_mask = dists_sq != np.inf
    directions[nonzero_mask] = vecs[nonzero_mask] / np.sqrt(dists_sq[nonzero_mask])[:, None]
 
    # Ray-sphere intersection test (Earth at origin)
    # Equation: ||pos + t*dir||^2 = R^2 → t^2 + 2*(pos•dir)*t + ||pos||^2 - R^2 = 0
    pos_dot_dir = np.sum(positions[:, None, :] * directions, axis=2)  # shape: (N, N)
    pos_norm_sq = np.sum(positions[:, None, :]**2, axis=2)
    R2 = earth_radius_km**2
    discriminant = pos_dot_dir**2 - (pos_norm_sq - R2)
 
    # LOS exists if discriminant <= 0 (no intersection with Earth)
    adj_matrix[compute_mask] = discriminant[compute_mask] <= 0
 
    # Remove self-connections
    np.fill_diagonal(adj_matrix, 0)
 
    return adj_matrix, keys



def addGroundStationConnections(self, sat_positions):
        #Add ground station connections to already existing satellite matrix
        # Current adjacency matrix size
        N = len(keys)
        sat_keys = list(satellites.keys())
    
        # Prepare positions arrays
        sat_positions = np.array([satellites[k].position for k in sat_keys], dtype=float)
        gs_keys = list(groundStations.keys())
        gs_positions = np.array([groundStations[k].position for k in gs_keys], dtype=float)
    
        # New adjacency matrix size
        total_objects = N + len(gs_keys)
        new_adj_matrix = np.zeros((total_objects, total_objects), dtype=bool)
    
        # Copy existing satellite-satellite adjacency
        new_adj_matrix[:N, :N] = adj_matrix
    
        # For each ground station, compute LOS to each satellite
        for i, gs_pos in enumerate(gs_positions):
            gs_idx = N + i  # row/column index in new matrix
            vec = sat_positions - gs_pos  # vector from GS to satellites
            up = gs_pos / np.linalg.norm(gs_pos)
            los_mask = np.dot(vec, up) > 0  # satellite above horizon
        
            if earth_radius_km is not None:
                # Optional: discard satellites blocked by Earth
                gs_norm_sq = np.sum(gs_pos**2)
                sat_norm_sq = np.sum(sat_positions**2, axis=1)
                # Solve t^2 + 2*(p•d)*t + ||p||^2 - R^2 = 0
                directions = vec / np.linalg.norm(vec, axis=1)[:, None]
                p_dot_d = np.sum(gs_pos * directions, axis=1)
                discriminant = p_dot_d**2 - (gs_norm_sq - earth_radius_km**2)
                los_mask &= discriminant <= 0
        
            # Update adjacency matrix (GS ↔ satellite)
            for j, visible in enumerate(los_mask):
                if visible:
                    sat_idx = j  # satellite index in old keys
                    new_adj_matrix[gs_idx, sat_idx] = True
                    new_adj_matrix[sat_idx, gs_idx] = True  # symmetric
    
        # New keys list
        new_keys = keys + gs_keys
        return new_adj_matrix, new_keys