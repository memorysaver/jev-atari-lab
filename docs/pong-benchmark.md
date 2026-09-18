# What counts as better Pong performance?

Pong's primary gameplay measure is episode return: points scored minus points
conceded. Each point contributes +1 or -1. A native match ends when either player
reaches 21, so a completed 21-10 win returns +11 and a 10-21 loss returns -11.
The highest possible match return is +21. These rules come directly from the
[pinned ALE implementation](https://github.com/Farama-Foundation/Arcade-Learning-Environment/blob/v0.11.2/src/ale/games/supported/Pong.cpp).

There is no single Atari evaluation configuration shared by all publications.
ALE's [evaluation methodology paper](https://arxiv.org/abs/1709.06009) explains how
protocol differences affect comparisons. Match the game/mode/difficulty, input
representation, action set, action repeat, sticky actions, reset procedure,
episode cap, and training budget before comparing published scores.

## What our current numbers mean

Our fixed-frame pilot uses four development seeds, each with 2,000 controlled raw
frames (33.33 simulated seconds), rather than complete matches. The v2 Jev
question's aggregate return of -3 means a mean of -0.75 per short episode;
the Python 4px control's -14 means -3.5 per short episode. Those are valid
within-protocol descriptive comparisons, not full-match benchmark scores.
A zero-return short episode can be a long rally with no scoring. It does not
establish a draw, a win, or mastery. Report scored and conceded points separately.

Jev sees RAM-derived object positions and a hand-authored tracking question.
The model is pretrained. This is a different information and prior-knowledge
setting from a general agent learning from pixels from scratch. We cannot use
these pilot results to claim superiority over published pixel-based RL systems.

## Proposed evaluation milestones

These are future design recommendations, not additional authorized live runs or
a claim that a particular number of episodes is an official universal standard.

1. Freeze each question before evaluation. Compare it with the prior question,
   a random policy, and a stronger handwritten controller under identical settings.
2. Use full native matches, with a predeclared frame/API safety cap. Preserve and
   report unfinished games and their returns; never turn them into full-match wins
   or silently omit expensive episodes.
3. Use multiple fresh evaluation seeds and independent model samples. Report mean
   episode return, uncertainty, full-match win rate, and completion rate. State how
   incomplete games enter each denominator. Paired seed differences help compare
   programs, but identical seeds do not make diverging policies visit identical states.
4. Keep final-test seeds out of teacher feedback and question selection. To establish
   learning, evaluate multiple teacher rounds and independent runs against an
   equal-budget proposal process without trajectory feedback.
5. Report environment frames, decisions, API attempts (including failures), tokens,
   and elapsed API time separately. Better score and better cost efficiency are
   different claims.

Confidence, action frequencies, and agreement with a written 4px rule help diagnose
behavior. They are not substitutes for actual reward. High confidence does not
establish a high probability of winning; exact rule adherence does not establish
that the rule is a good strategy.
