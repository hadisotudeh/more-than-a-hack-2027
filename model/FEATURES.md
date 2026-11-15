# Active model input inventory

Exact selected inputs for `skillcorner_20_compact`: 121 dead-ball inputs and 108 team-possession inputs.
`shared` has no team perspective. In the dead-ball design, `team1` is one team perspective and `team2`
is the opposite view; inference averages both swapped views. `own` and `opp` are relative to each view.
Temporal windows use seconds and reset at halftime. Some inputs appear in both classifiers.

## Dead

| Input | Feature group |
| --- | --- |
| `shared.ball_miss_run_s` | Ball availability |
| `shared.ball_oob` | Pitch geometry |
| `shared.ball_oob_m1` | Pitch geometry |
| `shared.ball_oob_m3` | Pitch geometry |
| `shared.ball_proj_exit_s` | Stop/restart timing |
| `shared.ball_seen_m3.0` | Ball availability |
| `shared.ball_since_seen_s` | Ball availability |
| `shared.ball_speed` | Ball motion |
| `shared.ball_speed_after_1s` | Ball motion |
| `shared.ball_speed_after_2s` | Ball motion |
| `shared.ball_speed_before_1s` | Ball motion |
| `shared.ball_speed_before_2s` | Ball motion |
| `shared.ball_speed_m1.0` | Ball motion |
| `shared.ball_speed_m3.0` | Ball motion |
| `shared.ball_still_m1` | Ball motion |
| `shared.ball_to_centre` | Pitch geometry |
| `shared.ball_to_corner` | Pitch geometry |
| `shared.ball_to_goalline` | Pitch geometry |
| `shared.ball_to_touchline` | Pitch geometry |
| `shared.ball_until_seen_s` | Ball availability |
| `shared.ball_window_speed` | Ball motion |
| `shared.block_motion_m3` | Player/team movement |
| `shared.ctrl_any_m1` | Control |
| `shared.dmin_any` | Player proximity |
| `shared.frac_fast_m3` | Player/team movement |
| `shared.kickoff_shape` | Restart shape |
| `shared.kickoff_shape_m3` | Restart shape |
| `shared.last_ball_oob` | Pitch geometry |
| `shared.n5_any` | Player proximity |
| `shared.since_ctrl_any` | Control |
| `shared.since_oob_s` | Stop/restart timing |
| `shared.since_still_s` | Stop/restart timing |
| `shared.speed_delta_1s` | Player/team movement |
| `shared.speed_delta_2s` | Player/team movement |
| `shared.speed_max_m1` | Player/team movement |
| `shared.speed_mean_m1.0` | Player/team movement |
| `shared.speed_mean_m3.0` | Player/team movement |
| `shared.speed_mean_m6.0` | Player/team movement |
| `shared.speed_ratio_m1.0` | Player/team movement |
| `shared.speed_ratio_m3.0` | Player/team movement |
| `shared.speed_ratio_m6.0` | Player/team movement |
| `shared.spread_sum` | Team shape |
| `shared.until_ctrl_any` | Control |
| `shared.until_oob_s` | Stop/restart timing |
| `shared.until_still_s` | Stop/restart timing |
| `team1.ball_fwd_v_after` | Ball motion |
| `team1.ball_fwd_v_before` | Ball motion |
| `team1.ball_fwd_v_m1` | Ball motion |
| `team1.ball_minus_opp_cx` | Ball relative to teams |
| `team1.ball_minus_own_cx` | Ball relative to teams |
| `team1.ball_xa` | Ball relative to teams |
| `team1.ball_xa_m1` | Ball relative to teams |
| `team1.d_diff` | Player proximity |
| `team1.d_diff_m0.5` | Player proximity |
| `team1.d_diff_m1.0` | Player proximity |
| `team1.d_diff_m3.0` | Player proximity |
| `team1.last_toucher` | Touches |
| `team1.next_toucher` | Touches |
| `team1.opp_ctrl_m0.5` | Control |
| `team1.opp_ctrl_m1.0` | Control |
| `team1.opp_ctrl_m3.0` | Control |
| `team1.opp_cx` | Team shape |
| `team1.opp_d` | Player proximity |
| `team1.opp_fwd_v` | Player/team movement |
| `team1.opp_fwd_v_delta` | Player/team movement |
| `team1.opp_fwd_v_m3` | Player/team movement |
| `team1.opp_in_opp` | Team shape |
| `team1.opp_n5` | Player proximity |
| `team1.opp_since_ctrl` | Control |
| `team1.opp_since_touch` | Touches |
| `team1.opp_sx` | Team shape |
| `team1.opp_sx_delta` | Team shape |
| `team1.opp_sx_m1.0` | Team shape |
| `team1.opp_sx_m3.0` | Team shape |
| `team1.opp_sy` | Team shape |
| `team1.opp_touches_after` | Touches |
| `team1.opp_until_ctrl` | Control |
| `team1.opp_until_touch` | Touches |
| `team1.opp_v` | Player/team movement |
| `team1.opp_xmax` | Team shape |
| `team1.opp_xmin2` | Team shape |
| `team1.own_ctrl_m0.5` | Control |
| `team1.own_ctrl_m1.0` | Control |
| `team1.own_ctrl_m3.0` | Control |
| `team1.own_cx` | Team shape |
| `team1.own_d` | Player proximity |
| `team1.own_fwd_v` | Player/team movement |
| `team1.own_fwd_v_delta` | Player/team movement |
| `team1.own_fwd_v_m3` | Player/team movement |
| `team1.own_in_opp` | Team shape |
| `team1.own_n5` | Player proximity |
| `team1.own_since_ctrl` | Control |
| `team1.own_since_touch` | Touches |
| `team1.own_sx` | Team shape |
| `team1.own_sx_delta` | Team shape |
| `team1.own_sx_m1.0` | Team shape |
| `team1.own_sx_m3.0` | Team shape |
| `team1.own_sy` | Team shape |
| `team1.own_touches_after` | Touches |
| `team1.own_until_ctrl` | Control |
| `team1.own_until_touch` | Touches |
| `team1.own_v` | Player/team movement |
| `team1.own_xmax` | Team shape |
| `team1.own_xmin2` | Team shape |
| `team1.since_ctrl_diff` | Control |
| `team1.until_ctrl_diff` | Control |
| `team2.ball_fwd_v_after` | Ball motion |
| `team2.ball_fwd_v_before` | Ball motion |
| `team2.ball_fwd_v_m1` | Ball motion |
| `team2.ball_minus_opp_cx` | Ball relative to teams |
| `team2.ball_minus_own_cx` | Ball relative to teams |
| `team2.ball_xa` | Ball relative to teams |
| `team2.ball_xa_m1` | Ball relative to teams |
| `team2.d_diff` | Player proximity |
| `team2.d_diff_m0.5` | Player proximity |
| `team2.d_diff_m1.0` | Player proximity |
| `team2.d_diff_m3.0` | Player proximity |
| `team2.last_toucher` | Touches |
| `team2.next_toucher` | Touches |
| `team2.since_ctrl_diff` | Control |
| `team2.until_ctrl_diff` | Control |

## Possession

| Input | Feature group |
| --- | --- |
| `team.ball_fwd_v_after` | Ball motion |
| `team.ball_fwd_v_before` | Ball motion |
| `team.ball_fwd_v_m1` | Ball motion |
| `team.ball_minus_opp_cx` | Ball relative to teams |
| `team.ball_minus_own_cx` | Ball relative to teams |
| `team.ball_xa` | Ball relative to teams |
| `team.ball_xa_m1` | Ball relative to teams |
| `team.d_diff` | Player proximity |
| `team.d_diff_m0.5` | Player proximity |
| `team.d_diff_m1.0` | Player proximity |
| `team.d_diff_m3.0` | Player proximity |
| `team.last_toucher` | Touches |
| `team.next_toucher` | Touches |
| `team.opp_ctrl_m0.5` | Control |
| `team.opp_ctrl_m1.0` | Control |
| `team.opp_ctrl_m3.0` | Control |
| `team.opp_cx` | Team shape |
| `team.opp_d` | Player proximity |
| `team.opp_fwd_v` | Player/team movement |
| `team.opp_fwd_v_delta` | Player/team movement |
| `team.opp_fwd_v_m3` | Player/team movement |
| `team.opp_in_opp` | Team shape |
| `team.opp_n2` | Player proximity |
| `team.opp_n5` | Player proximity |
| `team.opp_since_ctrl` | Control |
| `team.opp_since_touch` | Touches |
| `team.opp_sx` | Team shape |
| `team.opp_sx_delta` | Team shape |
| `team.opp_sx_m1.0` | Team shape |
| `team.opp_sx_m3.0` | Team shape |
| `team.opp_sy` | Team shape |
| `team.opp_touches_after` | Touches |
| `team.opp_until_ctrl` | Control |
| `team.opp_until_touch` | Touches |
| `team.opp_v` | Player/team movement |
| `team.opp_xmax` | Team shape |
| `team.opp_xmin2` | Team shape |
| `team.own_ctrl_m0.5` | Control |
| `team.own_ctrl_m1.0` | Control |
| `team.own_ctrl_m3.0` | Control |
| `team.own_cx` | Team shape |
| `team.own_d` | Player proximity |
| `team.own_fwd_v` | Player/team movement |
| `team.own_fwd_v_delta` | Player/team movement |
| `team.own_fwd_v_m3` | Player/team movement |
| `team.own_in_opp` | Team shape |
| `team.own_n2` | Player proximity |
| `team.own_n5` | Player proximity |
| `team.own_since_ctrl` | Control |
| `team.own_since_touch` | Touches |
| `team.own_sx` | Team shape |
| `team.own_sx_delta` | Team shape |
| `team.own_sx_m1.0` | Team shape |
| `team.own_sx_m3.0` | Team shape |
| `team.own_sy` | Team shape |
| `team.own_touches_after` | Touches |
| `team.own_touches_before` | Touches |
| `team.own_until_ctrl` | Control |
| `team.own_until_touch` | Touches |
| `team.own_v` | Player/team movement |
| `team.own_xmax` | Team shape |
| `team.own_xmin2` | Team shape |
| `team.since_ctrl_diff` | Control |
| `team.until_ctrl_diff` | Control |
| `shared.ball_miss_run_s` | Ball availability |
| `shared.ball_oob` | Pitch geometry |
| `shared.ball_oob_m1` | Pitch geometry |
| `shared.ball_oob_m3` | Pitch geometry |
| `shared.ball_proj_exit_s` | Stop/restart timing |
| `shared.ball_seen_m3.0` | Ball availability |
| `shared.ball_speed` | Ball motion |
| `shared.ball_speed_after_1s` | Ball motion |
| `shared.ball_speed_after_2s` | Ball motion |
| `shared.ball_speed_before_1s` | Ball motion |
| `shared.ball_speed_before_2s` | Ball motion |
| `shared.ball_speed_m1.0` | Ball motion |
| `shared.ball_speed_m3.0` | Ball motion |
| `shared.ball_still_m1` | Ball motion |
| `shared.ball_to_centre` | Pitch geometry |
| `shared.ball_to_corner` | Pitch geometry |
| `shared.ball_to_goalline` | Pitch geometry |
| `shared.ball_to_touchline` | Pitch geometry |
| `shared.ball_until_seen_s` | Ball availability |
| `shared.ball_window_speed` | Ball motion |
| `shared.block_motion_m3` | Player/team movement |
| `shared.ctrl_any_m1` | Control |
| `shared.dmin_any` | Player proximity |
| `shared.frac_fast_m3` | Player/team movement |
| `shared.kickoff_shape` | Restart shape |
| `shared.kickoff_shape_m3` | Restart shape |
| `shared.last_ball_oob` | Pitch geometry |
| `shared.n5_any` | Player proximity |
| `shared.since_ctrl_any` | Control |
| `shared.since_oob_s` | Stop/restart timing |
| `shared.since_still_s` | Stop/restart timing |
| `shared.speed_delta_1s` | Player/team movement |
| `shared.speed_delta_2s` | Player/team movement |
| `shared.speed_max_m1` | Player/team movement |
| `shared.speed_mean_m1.0` | Player/team movement |
| `shared.speed_mean_m3.0` | Player/team movement |
| `shared.speed_mean_m6.0` | Player/team movement |
| `shared.speed_ratio_m1.0` | Player/team movement |
| `shared.speed_ratio_m3.0` | Player/team movement |
| `shared.speed_ratio_m6.0` | Player/team movement |
| `shared.spread_sum` | Team shape |
| `shared.until_ctrl_any` | Control |
| `shared.until_oob_s` | Stop/restart timing |
| `shared.until_still_s` | Stop/restart timing |
