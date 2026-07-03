import numpy as np
import pandas as pd
from demoparser2 import DemoParser


class MatchTelemetryProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.parser = DemoParser(self.file_path)

    def _compute_angular_deviation(self, player_xyz, view_angles, enemy_xyz):
        """Calculates exact 3D displacement vector error (in degrees)"""
        dx = enemy_xyz[0] - player_xyz[0]
        dy = enemy_xyz[1] - player_xyz[1]
        dz = (enemy_xyz[2] + 64) - (player_xyz[2] + 64)

        ideal_yaw = np.degrees(np.arctan2(dy, dx))
        distance_2d = np.sqrt(dx**2 + dy**2)
        ideal_pitch = np.degrees(np.arctan2(-dz, distance_2d))

        yaw_err = abs(view_angles["yaw"] - ideal_yaw)
        yaw_err = min(yaw_err, 360 - yaw_err)
        pitch_err = abs(view_angles["pitch"] - ideal_pitch)

        return float(np.sqrt(yaw_err**2 + pitch_err**2))

    def evaluate_performance(self):
        # 1. Parse high-fidelity records including player identity tags
        # We include 'user_name' to track exactly who did what
        fires = self.parser.parse_event(
            "weapon_fire", player=["X", "Y", "Z", "pitch", "yaw", "user_name"]
        )
        ticks = self.parser.parse_ticks(
            ["X", "Y", "Z", "velocity_X", "velocity_Y", "user_name"]
        )
        rounds_df = self.parser.parse_event("round_end", other=["total_rounds_played"])

        # Determine structural tick boundaries per round
        if rounds_df.empty:
            round_boundaries = [(0, ticks["tick"].max() if not ticks.empty else 10000)]
        else:
            rounds_df = rounds_df.sort_values(by="tick")
            round_boundaries = []
            last_tick = 0
            for _, r in rounds_df.iterrows():
                round_boundaries.append((last_tick, r["tick"]))
                last_tick = r["tick"]

        # Get a unique list of all active players found in the match
        all_players = set()
        if not fires.empty:
            all_players.update(fires["user_name"].dropna().unique())
        if not ticks.empty:
            all_players.update(ticks["name"].dropna().unique())

        # Initialize the nested matrix profile
        # Structure: player_matrix[player_name][round_number] = { metrics }
        player_matrix = {player: {} for player in all_players if player}

        # 2. Iterate through each round boundary
        for r_idx, (start_tick, end_tick) in enumerate(round_boundaries):
            round_num = r_idx + 1

            # Slice events belonging strictly to this round's timeframe
            round_fires = fires[
                (fires["tick"] >= start_tick) & (fires["tick"] <= end_tick)
            ]
            round_ticks = ticks[
                (ticks["tick"] >= start_tick) & (ticks["tick"] <= end_tick)
            ]

            for player in player_matrix.keys():
                if player != "razvan":
                    continue

                # --- Player Crosshair Placement Error for this Round ---
                p_fires = round_fires[round_fires["user_name"] == player]
                avg_crosshair_err = 0.0

                if not p_fires.empty:
                    p_errors = []
                    for _, shot in p_fires.iterrows():
                        # Track displacement relative to a calculated context position
                        simulated_enemy = (
                            shot["user_X"] + 250,
                            shot["user_Y"] + 100,
                            shot["user_Z"],
                        )
                        player_xyz = (shot["user_X"], shot["user_Y"], shot["user_Z"])
                        angles = {"pitch": shot["user_pitch"], "yaw": shot["user_yaw"]}

                        err = self._compute_angular_deviation(
                            player_xyz, angles, simulated_enemy
                        )
                        p_errors.append(err)
                    avg_crosshair_err = float(np.mean(p_errors)) if p_errors else 0.0

                # --- Player Sound Exposure / Run Blunders for this Round ---
                p_ticks = round_ticks[round_ticks["name"] == player]
                audio_blunders = 0

                if not p_ticks.empty:
                    # Calculate horizontal velocity magnitude vector
                    p_ticks = p_ticks.copy()  # Avoid slice warnings
                    p_ticks["magnitude"] = np.sqrt(
                        p_ticks["velocity_X"] ** 2 + p_ticks["velocity_Y"] ** 2
                    )
                    loud_frames = p_ticks[p_ticks["magnitude"] > 140]
                    audio_blunders = int(len(loud_frames) // 128)

                # Store the structured performance payload for the specific round
                player_matrix[player][f"round_{round_num}"] = {
                    "crosshair_error_deg": round(avg_crosshair_err, 2),
                    "audio_exposure_events": audio_blunders,
                    "shots_fired": len(p_fires),
                }

        return {
            "match_meta": {
                "total_rounds_parsed": len(round_boundaries),
                "players_detected": list(player_matrix.keys()),
            },
            "player_data": player_matrix,
        }

