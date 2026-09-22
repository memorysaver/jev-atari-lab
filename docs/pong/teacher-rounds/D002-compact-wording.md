# D002: compact restatement of conservative motion reliability

Proposal status: **frozen before evaluation** on 2026-09-22.

Author: interactive coordinator, after reading the teacher-study, question-diagnostic
and motion-probe reports. This is one manual diagnostic intervention. No isolated
teacher packet/API invocation or model-weight change exists; exact interactive
model version and token cost are not independently recorded. Inputs are the 80
previously inspected training states, so this does not erase development exposure.

Hypothesis: removing repeated explanations while preserving every condition may
improve execution of the conservative rule. Falsifiers include no overall gain,
continued uncertain-motion fallback failure, or loss of basic directional behavior.
The [prospective protocol](../wording-probe-protocol.md) freezes the measurements,
screen and 520-attempt/four-hour limit before access. No gameplay or final test.

## Parent and candidate

Parent: `pong-explicit-motion-reliability-v1`, exactly the **After** text in
[D001](D001-motion-reliability.md), also `PRECISE` in
[`motion_probe.py`](../../../src/jev_atari/motion_probe.py). The expanded control
is queried afresh; its historical negative result is not reused as a control answer.

Candidate: `pong-compact-motion-reliability-v1`:

```text
Read ball and player in observation.objects. For bbox [x,y,w,h], center_y=y+h/2; y increases down. Missing ball or player bbox: NOOP. Otherwise target=ball center_y. Set target=ball center_y+4*vy only when ALL are true: ball.velocity_valid=true; ball.velocity=[vx,vy] is known in pixels/raw-frame with vx>0; the last three observation.history samples have ball bboxes and strictly increasing offset_raw_frames; their two consecutive x changes have product>=0 AND their two consecutive y changes have product>=0 (zero allowed). Any false or unknown condition: keep current-height target. No extra time scaling or wall reflection. gap=target-player center_y. gap < -4: RIGHT (UP); gap > 4: LEFT (DOWN); otherwise NOOP. Use non-FIRE actions. Horizontal motion only gates lookahead. Act for four raw frames, then reconsider.
```

Only the question text differs inside expanded/compact model requests. A fixed v2
arm anchors current-height behavior. Wording, length and redundancy change together;
neither semantic equivalence inside Jev nor a pure length effect is assumed.

Evaluation results will be appended after the frozen run. Keep this proposal text,
the original program and the protocol unchanged, including if the candidate fails.
