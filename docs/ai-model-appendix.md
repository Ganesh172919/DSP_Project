# AI Model Appendix

This appendix consolidates challenge-level references, metric-level references, anomaly guidance, templates, and detailed review checklists.

## Liveness Challenge Reference

### Blink 3 times

- Challenge id: `blink_count`
- Category: `eye`
- Difficulty: `1`
- Verifier: `blink_count`
- Prompt duration: `5` seconds
- Current description: Blink your eyes three times naturally at a steady pace.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Blink 5 times quickly

- Challenge id: `rapid_blink_5`
- Category: `eye`
- Difficulty: `2`
- Verifier: `blink_count`
- Prompt duration: `6` seconds
- Current description: Blink your eyes five times rapidly.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Wink left eye

- Challenge id: `wink_left`
- Category: `eye`
- Difficulty: `2`
- Verifier: `wink_left`
- Prompt duration: `4` seconds
- Current description: Close only your left eye briefly.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Wink right eye

- Challenge id: `wink_right`
- Category: `eye`
- Difficulty: `2`
- Verifier: `wink_right`
- Prompt duration: `4` seconds
- Current description: Close only your right eye briefly.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Look up

- Challenge id: `gaze_up`
- Category: `eye`
- Difficulty: `2`
- Verifier: `gaze_up`
- Prompt duration: `4` seconds
- Current description: Look upward without moving your head.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Look down

- Challenge id: `gaze_down`
- Category: `eye`
- Difficulty: `2`
- Verifier: `gaze_down`
- Prompt duration: `4` seconds
- Current description: Look downward without moving your head.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Look left

- Challenge id: `gaze_left`
- Category: `eye`
- Difficulty: `2`
- Verifier: `gaze_left`
- Prompt duration: `4` seconds
- Current description: Look to your left without moving your head.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Look right

- Challenge id: `gaze_right`
- Category: `eye`
- Difficulty: `2`
- Verifier: `gaze_right`
- Prompt duration: `4` seconds
- Current description: Look to your right without moving your head.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Slowly close and open eyes

- Challenge id: `slow_close_open`
- Category: `eye`
- Difficulty: `2`
- Verifier: `slow_close_open`
- Prompt duration: `6` seconds
- Current description: Slowly close your eyes, hold for a moment, then open.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Open mouth wide

- Challenge id: `mouth_open`
- Category: `mouth`
- Difficulty: `1`
- Verifier: `mouth_open`
- Prompt duration: `4` seconds
- Current description: Open your mouth as wide as comfortable.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Smile

- Challenge id: `smile`
- Category: `mouth`
- Difficulty: `1`
- Verifier: `smile`
- Prompt duration: `4` seconds
- Current description: Give a natural, wide smile.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Puff your cheeks

- Challenge id: `puff_cheeks`
- Category: `mouth`
- Difficulty: `2`
- Verifier: `puff_cheeks`
- Prompt duration: `5` seconds
- Current description: Inflate your cheeks with air.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Move mouth left

- Challenge id: `mouth_left`
- Category: `mouth`
- Difficulty: `3`
- Verifier: `mouth_left`
- Prompt duration: `4` seconds
- Current description: Shift your mouth to the left side.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Move mouth right

- Challenge id: `mouth_right`
- Category: `mouth`
- Difficulty: `3`
- Verifier: `mouth_right`
- Prompt duration: `4` seconds
- Current description: Shift your mouth to the right side.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Purse lips

- Challenge id: `purse_lips`
- Category: `mouth`
- Difficulty: `2`
- Verifier: `purse_lips`
- Prompt duration: `4` seconds
- Current description: Push your lips forward into a kissing shape.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Mouth a phrase silently

- Challenge id: `mouth_phrase`
- Category: `mouth`
- Difficulty: `3`
- Verifier: `mouth_phrase`
- Prompt duration: `6` seconds
- Current description: Silently mouth the words 'open sesame'.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Stick out your tongue

- Challenge id: `tongue`
- Category: `mouth`
- Difficulty: `2`
- Verifier: `tongue`
- Prompt duration: `4` seconds
- Current description: Briefly stick out your tongue.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Turn head left

- Challenge id: `turn_left`
- Category: `head`
- Difficulty: `1`
- Verifier: `turn_left`
- Prompt duration: `5` seconds
- Current description: Slowly turn your head to the left.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Turn head right

- Challenge id: `turn_right`
- Category: `head`
- Difficulty: `1`
- Verifier: `turn_right`
- Prompt duration: `5` seconds
- Current description: Slowly turn your head to the right.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Tilt head left

- Challenge id: `tilt_left`
- Category: `head`
- Difficulty: `2`
- Verifier: `tilt_left`
- Prompt duration: `5` seconds
- Current description: Tilt your head to the left shoulder.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Tilt head right

- Challenge id: `tilt_right`
- Category: `head`
- Difficulty: `2`
- Verifier: `tilt_right`
- Prompt duration: `5` seconds
- Current description: Tilt your head to the right shoulder.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Nod up and down

- Challenge id: `nod`
- Category: `head`
- Difficulty: `1`
- Verifier: `nod`
- Prompt duration: `5` seconds
- Current description: Nod your head up and down slowly.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Shake head side to side

- Challenge id: `shake`
- Category: `head`
- Difficulty: `1`
- Verifier: `shake`
- Prompt duration: `5` seconds
- Current description: Shake your head left to right slowly.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Look over your shoulder

- Challenge id: `look_over_shoulder`
- Category: `head`
- Difficulty: `3`
- Verifier: `look_over_shoulder`
- Prompt duration: `6` seconds
- Current description: Turn your head far to one side as if looking behind you.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Raise eyebrows

- Challenge id: `brow_raise`
- Category: `expression`
- Difficulty: `1`
- Verifier: `brow_raise`
- Prompt duration: `4` seconds
- Current description: Raise both eyebrows as high as possible.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Frown

- Challenge id: `frown`
- Category: `expression`
- Difficulty: `2`
- Verifier: `frown`
- Prompt duration: `4` seconds
- Current description: Furrow your brows as if concentrating hard.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Show surprise

- Challenge id: `surprise`
- Category: `expression`
- Difficulty: `2`
- Verifier: `surprise`
- Prompt duration: `5` seconds
- Current description: Make a surprised face: raise brows, open eyes wide, open mouth slightly.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Look angry

- Challenge id: `angry`
- Category: `expression`
- Difficulty: `2`
- Verifier: `angry`
- Prompt duration: `5` seconds
- Current description: Make an angry face: furrow brows, narrow eyes, press lips.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Squint

- Challenge id: `squint`
- Category: `expression`
- Difficulty: `1`
- Verifier: `squint`
- Prompt duration: `4` seconds
- Current description: Narrow both eyes without closing them.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Move closer then further

- Challenge id: `distance_shift`
- Category: `distance`
- Difficulty: `1`
- Verifier: `distance_shift`
- Prompt duration: `6` seconds
- Current description: Lean towards the camera, then lean back.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Blink then smile

- Challenge id: `blink_then_smile`
- Category: `combined`
- Difficulty: `3`
- Verifier: `blink_then_smile`
- Prompt duration: `7` seconds
- Current description: Blink 2-3 times, then immediately smile.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Turn and blink

- Challenge id: `turn_blink`
- Category: `combined`
- Difficulty: `3`
- Verifier: `turn_blink`
- Prompt duration: `6` seconds
- Current description: Turn your head slightly while blinking.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Eyebrows up and open mouth

- Challenge id: `brow_raise_mouth`
- Category: `combined`
- Difficulty: `3`
- Verifier: `brow_raise_mouth`
- Prompt duration: `5` seconds
- Current description: Raise your eyebrows and open your mouth at the same time.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Nod then wink

- Challenge id: `nod_then_wink`
- Category: `combined`
- Difficulty: `3`
- Verifier: `nod_then_wink`
- Prompt duration: `7` seconds
- Current description: Nod your head, then give a right-eye wink.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Show a number with fingers

- Challenge id: `finger_count`
- Category: `cognitive`
- Difficulty: `2`
- Verifier: `finger_count`
- Prompt duration: `6` seconds
- Current description: Hold up 3 fingers near your face.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Touch your nose

- Challenge id: `touch_nose`
- Category: `cognitive`
- Difficulty: `2`
- Verifier: `touch_nose`
- Prompt duration: `5` seconds
- Current description: Briefly touch the tip of your nose with a fingertip.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

### Wave at the camera

- Challenge id: `wave`
- Category: `cognitive`
- Difficulty: `1`
- Verifier: `wave`
- Prompt duration: `5` seconds
- Current description: Give a short wave with your hand near your face.
- Main purpose: confirm that the user can generate a live, temporally grounded response to a prompted action.
- Current scoring style: thresholded rule-based verification with a human-readable message.
- Common false reject cause: low landmark quality, poor lighting, or fast motion.
- Common false accept risk: replayed sequences or synthetic compliance if challenge families become predictable.
- Future model idea: use a temporal compliance head trained specifically for this challenge semantics.

## Feature Metric Glossary

### ear_left

- Category: Eye geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for blink, wink, squint, and eye-open verification.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### ear_right

- Category: Eye geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for blink, wink, squint, and eye-open verification.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### ear_average

- Category: Eye geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for blink, wink, squint, and eye-open verification.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### eye_symmetry_score

- Category: Eye geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### inter_pupillary_distance

- Category: Eye geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### left_eye_width

- Category: Composite biometric metric
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### left_eye_height

- Category: Composite biometric metric
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### right_eye_width

- Category: Composite biometric metric
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### right_eye_height

- Category: Composite biometric metric
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### left_eye_medial_angle

- Category: Composite biometric metric
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### right_eye_medial_angle

- Category: Composite biometric metric
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### gaze_horizontal

- Category: Eye geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for gaze-direction liveness challenges.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### gaze_vertical

- Category: Eye geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for gaze-direction liveness challenges.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### left_iris_ratio

- Category: Eye geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### right_iris_ratio

- Category: Eye geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### left_brow_eye_dist

- Category: Eyebrow geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### right_brow_eye_dist

- Category: Eyebrow geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### brow_raise_score

- Category: Eyebrow geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for brow-raise, surprise, angry, and frown challenge logic.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### inter_brow_distance

- Category: Eyebrow geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### left_brow_arch

- Category: Eyebrow geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### right_brow_arch

- Category: Eyebrow geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### left_brow_length

- Category: Eyebrow geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### right_brow_length

- Category: Eyebrow geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### brow_symmetry_score

- Category: Eyebrow geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### nose_length

- Category: Nasal geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### nose_bridge_width

- Category: Nasal geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### alar_base_width

- Category: Nasal geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### columella_length

- Category: Nasal geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### nasolabial_angle

- Category: Nasal geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### nose_bridge_deviation

- Category: Nasal geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### nose_asymmetry

- Category: Nasal geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### mouth_width

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for mouth-open, phrase, smile-adjacent, and tongue checks.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### mouth_height

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for mouth-open, phrase, smile-adjacent, and tongue checks.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### mar

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for mouth-open, phrase, smile-adjacent, and tongue checks.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### smile_score

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for smile-specific liveness scoring and expression differentiation.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### upper_lip_height

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### lower_lip_height

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### lip_volume_ratio

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### cupid_bow_width

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### cupid_bow_depth

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### lip_symmetry_score

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### mouth_corner_angle

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### lip_to_chin

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### philtrum_width

- Category: Mouth and lip geometry
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### face_width

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### face_height

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### face_whr

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### face_shape

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### facial_third_upper

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### facial_third_middle

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### facial_third_lower

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### facial_asymmetry_index

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### chin_shape

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### chin_to_forehead

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### face_convexity_angle

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### yaw

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for head-turn, nod, shake, tilt, and framing feedback.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### pitch

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for head-turn, nod, shake, tilt, and framing feedback.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### roll

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for head-turn, nod, shake, tilt, and framing feedback.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### face_size_ratio

- Category: Global face geometry and pose
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used for distance-shift liveness and framing guidance.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### skin_analysis_available

- Category: Image and skin texture
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### lbp_texture

- Category: Composite biometric metric
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### skin_color

- Category: Image and skin texture
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### dark_circle_intensity_left

- Category: Image and skin texture
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### dark_circle_intensity_right

- Category: Image and skin texture
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### skin_color_consistency

- Category: Image and skin texture
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

### high_freq_texture_energy

- Category: Image and skin texture
- Source: extracted from landmarks or image-derived face regions in `feature_extractor.py`.
- Operational usage: Used as enrollment evidence, authentication evidence, or both.
- Enrollment role: may become part of the stored reference template or supporting context for later comparisons.
- Authentication role: helps explain why a live sample agrees with or diverges from enrollment.
- Model-upgrade note: future learned models can preserve this metric as an interpretable side channel.

## Review Templates

### Recognition Model Card

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### PAD Model Card

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Deepfake Detector Model Card

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Liveness Sequence Model Card

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Fusion Model Card

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### rPPG Module Card

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Bias Evaluation Template

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Threshold Calibration Template

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Model Release Checklist

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Incident Review Template

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Rollback Readiness Template

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Red-Team Scenario Template

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Dataset Acceptance Template

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Annotation Guideline Template

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

### Shadow Deployment Template

- Owner: document this explicitly.
- Subsystem: document this explicitly.
- Model or heuristic version: document this explicitly.
- Primary task: document this explicitly.
- Primary risks: document this explicitly.
- Training or calibration data: document this explicitly.
- Validation domains: document this explicitly.
- Known weak domains: document this explicitly.
- Fairness review status: document this explicitly.
- Security review status: document this explicitly.
- Latency budget: document this explicitly.
- Rollback plan: document this explicitly.

## Additional Governance Questions

### Governance Prompt 1

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 2

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 3

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 4

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 5

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 6

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 7

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 8

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 9

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 10

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 11

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 12

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 13

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 14

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 15

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 16

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 17

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 18

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 19

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 20

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 21

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 22

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 23

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 24

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 25

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 26

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 27

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 28

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 29

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 30

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 31

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 32

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 33

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 34

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 35

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 36

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 37

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 38

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 39

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 40

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 41

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 42

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 43

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 44

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 45

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 46

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 47

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 48

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 49

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 50

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 51

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 52

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 53

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 54

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 55

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 56

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 57

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 58

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 59

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 60

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 61

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 62

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 63

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 64

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 65

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 66

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 67

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 68

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 69

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 70

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 71

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 72

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 73

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 74

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 75

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 76

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 77

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 78

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 79

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 80

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 81

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 82

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 83

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 84

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 85

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 86

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 87

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 88

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 89

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 90

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 91

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 92

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 93

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 94

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 95

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 96

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 97

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 98

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 99

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 100

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 101

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 102

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 103

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 104

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 105

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 106

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 107

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 108

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 109

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 110

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 111

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 112

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 113

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 114

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 115

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 116

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 117

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 118

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 119

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 120

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 121

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 122

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 123

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 124

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 125

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 126

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 127

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 128

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 129

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 130

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 131

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 132

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 133

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 134

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 135

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 136

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 137

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 138

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 139

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 140

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 141

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 142

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 143

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 144

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 145

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 146

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 147

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 148

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 149

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 150

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 151

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 152

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 153

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 154

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 155

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 156

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 157

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 158

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 159

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?

### Governance Prompt 160

- What changed?
- Why now?
- Who approved it?
- What evidence was reviewed?
- What can go wrong?
- How will we notice?
- How will we recover?
- How do we explain it?
