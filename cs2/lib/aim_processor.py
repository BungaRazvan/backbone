import numpy as np
import pandas as pd
from demoparser2 import DemoParser


class LiveEngagementProcessor:
    def __init__(self, file_path, target_player=None):
        """
        Initialization setup layer.
        Pass a specific string name (e.g., "razvan") to lock analysis to one player profile.
        """

        self.file_path = file_path
        self.target_player = "razvan"
        self.parser = DemoParser(self.file_path)

    def calculate_ideal_target_angles(self, player_xyz, target_enemy_xyz):
        """
        Calculates the absolute 3D vector (Pitch/Yaw) required to point your
        crosshair precisely at an active enemy player's head level.
        """

        dx = target_enemy_xyz[0] - player_xyz[0]
        dy = target_enemy_xyz[1] - player_xyz[1]
        dz = (target_enemy_xyz[2] + 64) - (
            player_xyz[2] + 64
        )  # Eye-level translation offset

        ideal_yaw = np.degrees(np.arctan2(dy, dx))
        distance_2d = np.sqrt(dx**2 + dy**2)
        ideal_pitch = np.degrees(np.arctan2(-dz, distance_2d))

        return {"pitch": round(ideal_pitch, 2), "yaw": round(ideal_yaw, 2)}

    def calculate_alignment_error(self, current_aim, ideal_view):
        """
        Measures the absolute angular distance (in degrees) between your
        current aim orientation and the perfect tracking vector.
        """

        yaw_error = abs(current_aim["yaw"] - ideal_view["yaw"])
        yaw_error = min(
            yaw_error, 360 - yaw_error
        )  # Handle polar coordinate wraparound
        pitch_error = abs(current_aim["pitch"] - ideal_view["pitch"])

        total_error = np.sqrt(yaw_error**2 + pitch_error**2)
        return round(float(total_error), 2)

    def evaluate_performance(self):
        # 1. Parse high-fidelity global frame logs using uniform naming conventions
        ticks = self.parser.parse_ticks(
            ["X", "Y", "Z", "pitch", "yaw", "user_name", "team_num", "is_alive"]
        )
        fires = self.parser.parse_event("weapon_fire", player=["user_name"])
        rounds_df = self.parser.parse_event("round_end")

        print(ticks.head())
        if ticks.empty:
            return {
                "error": "No usable data network ticks extracted from match demo container."
            }

        # Dynamically discover all active profiles utilizing the standardized user_name header column
        all_detected_players = (
            list(ticks["name"].dropna().unique()) if "name" in ticks.columns else []
        )

        # Fallback handling: If target player is missing or omitted, default to the first player found
        active_subject = (
            self.target_player
            if self.target_player in all_detected_players
            else (all_detected_players[0] if all_detected_players else None)
        )

        if not active_subject:
            return {
                "error": "No valid player identities could be recovered from this demo file."
            }

        # 2. Extract chronological round boundaries
        round_boundaries = []
        if not rounds_df.empty:
            rounds_df = rounds_df.sort_values(by="tick")
            last_tick = 0

            for _, r in rounds_df.iterrows():
                round_boundaries.append((last_tick, r["tick"]))
                last_tick = r["tick"]
        else:
            round_boundaries = [(0, ticks["tick"].max())]

        # 3. Apply Vectorized Pre-Filters immediately to reduce inner loop overhead
        subject_ticks = ticks[ticks["name"] == active_subject]
        subject_fires = (
            fires[fires["user_name"] == active_subject]
            if not fires.empty
            else pd.DataFrame()
        )

        if subject_ticks.empty:
            return {
                "error": f"Target player identity '{active_subject}' could not be located inside data frame vectors."
            }

        subject_team = subject_ticks["team_num"].iloc[0]
        round_by_round_output = {}

        # 4. Main Timeline Progression Sequence
        for r_idx, (start_tick, end_tick) in enumerate(round_boundaries):
            round_num = r_idx + 1

            # Slice down target data sets strictly into this round window
            r_s_ticks = subject_ticks[
                (subject_ticks["tick"] >= start_tick)
                & (subject_ticks["tick"] <= end_tick)
            ]
            r_s_fires = (
                subject_fires[
                    (subject_fires["tick"] >= start_tick)
                    & (subject_fires["tick"] <= end_tick)
                ]
                if not subject_fires.empty
                else pd.DataFrame()
            )

            # Extract opposing team metrics active inside this specific time slice
            r_enemy_ticks = ticks[
                (ticks["tick"] >= start_tick)
                & (ticks["tick"] <= end_tick)
                & (ticks["team_num"] != subject_team)
            ]

            tracking_overlay_timeline = []

            if not r_s_ticks.empty:
                # Downsample data points to every 16th network packet tick to save memory
                sampled_frames = r_s_ticks.iloc[::16]

                for _, frame in sampled_frames.iterrows():
                    current_tick_id = frame["tick"]
                    player_xyz = (frame["X"], frame["Y"], frame["Z"])

                    # Capture your exact aim trajectory attributes at this frame
                    current_aim = {
                        "pitch": round(frame["pitch"], 2),
                        "yaw": round(frame["yaw"], 2),
                    }

                    # Locate opposing elements alive at this microsecond marker
                    current_frame_team = frame["team_num"]
                    living_enemies = r_enemy_ticks[
                        (r_enemy_ticks["tick"] == current_tick_id)
                        & (r_enemy_ticks["is_alive"] == True)
                        & (r_enemy_ticks["team_num"] != current_frame_team)
                    ]

                    enemies_evaluation = []
                    for _, enemy in living_enemies.iterrows():
                        enemy_name = enemy["name"]
                        enemy_xyz = (enemy["X"], enemy["Y"], enemy["Z"])

                        # Compute dynamic geometry targets relative to enemy positional name tags
                        ideal_angles = self.calculate_ideal_target_angles(
                            player_xyz, enemy_xyz
                        )
                        angular_error = self.calculate_alignment_error(
                            current_aim, ideal_angles
                        )

                        enemies_evaluation.append(
                            {
                                "enemy_player_name": enemy_name,
                                "ideal_target_view": ideal_angles,
                                "current_aim_offset_deg": angular_error,
                                "is_on_target": angular_error
                                < 3.5,  # Crosshair within striking box limits
                            }
                        )

                    tracking_overlay_timeline.append(
                        {
                            "tick": int(current_tick_id),
                            "player_pos": player_xyz,
                            "current_aim": current_aim,
                            "active_enemy_targets": enemies_evaluation,
                        }
                    )

            # Commit finalized structural package array mapping
            round_by_round_output[f"Round {round_num}"] = {
                "shots_fired_count": len(r_s_fires),
                "tracking_timeline": tracking_overlay_timeline,
            }

        return {
            "analysis_meta": {
                "target_player_subject": active_subject,
                "total_rounds_processed": len(round_boundaries),
                "players_detected": all_detected_players,
            },
            "performance_profile": round_by_round_output,
        }
