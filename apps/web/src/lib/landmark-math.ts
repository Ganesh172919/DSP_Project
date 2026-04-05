type Point = { x: number; y: number; z?: number };

const leftEye = [33, 160, 158, 133, 153, 144];
const rightEye = [362, 385, 387, 263, 373, 380];
const leftBrow = [70, 63, 105];
const rightBrow = [336, 296, 334];
const mouth = [61, 13, 14, 291];
const leftCheek = 234;
const rightCheek = 454;
const chin = 152;
const forehead = 10;
const leftIris = [468, 469, 470, 471, 472];
const rightIris = [473, 474, 475, 476, 477];

function distance(a: Point, b: Point) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function midpoint(a: Point, b: Point) {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

function avg(points: Point[]) {
  const total = points.reduce(
    (acc, point) => ({ x: acc.x + point.x, y: acc.y + point.y, z: (acc.z ?? 0) + (point.z ?? 0) }),
    { x: 0, y: 0, z: 0 }
  );
  return {
    x: total.x / points.length,
    y: total.y / points.length,
    z: (total.z ?? 0) / points.length
  };
}

function ear(landmarks: Point[], indices: number[]) {
  const [p1, p2, p3, p4, p5, p6] = indices.map((index) => landmarks[index]);
  return (distance(p2, p6) + distance(p3, p5)) / (2 * distance(p1, p4));
}

function boundingBox(landmarks: Point[]) {
  const xs = landmarks.map((point) => point.x);
  const ys = landmarks.map((point) => point.y);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys)
  };
}

function clamp(value: number, min = 0, max = 1) {
  return Math.max(min, Math.min(max, value));
}

export function extractMetrics(rawLandmarks: Point[] = [], handLandmarks: Point[][] = []) {
  if (!rawLandmarks.length) {
    return {
      face_present: false,
      face_count: 0,
      face_size_ratio: 0,
      ear_left: 0,
      ear_right: 0,
      mar: 0,
      smile_score: 0,
      brow_raise_score: 0,
      yaw: 0,
      pitch: 0,
      roll: 0,
      gaze_horizontal: 0,
      gaze_vertical: 0,
      inter_pupillary_distance: 0,
      face_width: 0,
      face_height: 0,
      face_center_x: 0,
      face_center_y: 0,
      eye_line_y: 0,
      face_top_margin: 0,
      face_bottom_margin: 0,
      face_left_margin: 0,
      face_right_margin: 0,
      alignment_score: 0,
      chin_to_forehead: 0,
      hand_count: 0,
      hand_near_face: false,
      quality_hint: "No face"
    };
  }

  const box = boundingBox(rawLandmarks);
  const faceWidth = box.maxX - box.minX;
  const faceHeight = box.maxY - box.minY;
  const leftEyeAvg = avg(leftEye.map((index) => rawLandmarks[index]));
  const rightEyeAvg = avg(rightEye.map((index) => rawLandmarks[index]));
  const eyeMid = midpoint(leftEyeAvg, rightEyeAvg);
  const mouthLeft = rawLandmarks[mouth[0]];
  const mouthTop = rawLandmarks[mouth[1]];
  const mouthBottom = rawLandmarks[mouth[2]];
  const mouthRight = rawLandmarks[mouth[3]];
  const nose = rawLandmarks[1];
  const cheekLeftPoint = rawLandmarks[leftCheek];
  const cheekRightPoint = rawLandmarks[rightCheek];
  const leftBrowAvg = avg(leftBrow.map((index) => rawLandmarks[index]));
  const rightBrowAvg = avg(rightBrow.map((index) => rawLandmarks[index]));
  const irisLeftAvg = avg(leftIris.map((index) => rawLandmarks[index]));
  const irisRightAvg = avg(rightIris.map((index) => rawLandmarks[index]));
  const chinPoint = rawLandmarks[chin];
  const foreheadPoint = rawLandmarks[forehead];

  const roll = Math.atan2(rightEyeAvg.y - leftEyeAvg.y, rightEyeAvg.x - leftEyeAvg.x);
  const normalizedNoseX = (nose.x - (cheekLeftPoint.x + cheekRightPoint.x) / 2) / faceWidth;
  const normalizedNoseY = (nose.y - (eyeMid.y + mouthTop.y) / 2) / faceHeight;
  const gazeHorizontal = ((irisLeftAvg.x - leftEyeAvg.x) + (irisRightAvg.x - rightEyeAvg.x)) / 2 / faceWidth;
  const gazeVertical = ((irisLeftAvg.y - leftEyeAvg.y) + (irisRightAvg.y - rightEyeAvg.y)) / 2 / faceHeight;
  const mouthWidth = distance(mouthLeft, mouthRight);
  const mouthHeight = distance(mouthTop, mouthBottom);
  const browRaiseLeft = distance(leftBrowAvg, leftEyeAvg) / faceHeight;
  const browRaiseRight = distance(rightBrowAvg, rightEyeAvg) / faceHeight;
  const handCount = handLandmarks.length;
  const faceCenter = { x: (box.minX + box.maxX) / 2, y: (box.minY + box.maxY) / 2 };
  const handNearFace = handLandmarks.some((hand) => {
    const palm = avg(hand.slice(0, 5));
    return distance(palm, faceCenter) < faceWidth * 0.75;
  });
  const rollDegrees = (roll * 180) / Math.PI;
  const faceTopMargin = box.minY;
  const faceBottomMargin = 1 - box.maxY;
  const faceLeftMargin = box.minX;
  const faceRightMargin = 1 - box.maxX;
  const sizeScore = clamp((faceWidth * faceHeight - 0.04) / 0.07);
  const centerScore = clamp(1 - (Math.abs(faceCenter.x - 0.5) / 0.22));
  const eyeLineScore = clamp(1 - (Math.abs(eyeMid.y - 0.40) / 0.22));
  const marginScore = clamp(Math.min(faceTopMargin, faceBottomMargin) / 0.05);
  const poseScore = clamp(1 - Math.abs(rollDegrees) / 20);
  const alignmentScore = clamp(
    0.30 * sizeScore +
    0.25 * centerScore +
    0.25 * eyeLineScore +
    0.10 * marginScore +
    0.10 * poseScore
  );

  const qualityHint =
    faceWidth < 0.15
      ? "Move closer to the camera"
      : eyeMid.y > 0.50 || faceBottomMargin < 0.05
        ? "Raise the camera or tilt screen upward"
        : eyeMid.y < 0.15 || faceTopMargin < 0.02
          ? "Lower the camera slightly"
          : faceCenter.x < 0.30
            ? "Move your face to the right"
            : faceCenter.x > 0.70
              ? "Move your face to the left"
              : Math.abs(roll) > 0.30
        ? "Straighten your head"
        : "Ready";

  return {
    face_present: true,
    face_size_ratio: Number((faceWidth * faceHeight).toFixed(4)),
    ear_left: Number(ear(rawLandmarks, leftEye).toFixed(4)),
    ear_right: Number(ear(rawLandmarks, rightEye).toFixed(4)),
    mar: Number((mouthHeight / mouthWidth).toFixed(4)),
    smile_score: Number(((mouthWidth / faceWidth) * 2.2).toFixed(4)),
    brow_raise_score: Number((((browRaiseLeft + browRaiseRight) / 2) * 9).toFixed(4)),
    yaw: Number((normalizedNoseX * 180).toFixed(2)),
    pitch: Number((normalizedNoseY * 180).toFixed(2)),
    roll: Number(((roll * 180) / Math.PI).toFixed(2)),
    gaze_horizontal: Number((gazeHorizontal * 100).toFixed(2)),
    gaze_vertical: Number((gazeVertical * 100).toFixed(2)),
    inter_pupillary_distance: Number(distance(leftEyeAvg, rightEyeAvg).toFixed(4)),
    face_width: Number(faceWidth.toFixed(4)),
    face_height: Number(faceHeight.toFixed(4)),
    face_center_x: Number(faceCenter.x.toFixed(4)),
    face_center_y: Number(faceCenter.y.toFixed(4)),
    eye_line_y: Number(eyeMid.y.toFixed(4)),
    face_top_margin: Number(faceTopMargin.toFixed(4)),
    face_bottom_margin: Number(faceBottomMargin.toFixed(4)),
    face_left_margin: Number(faceLeftMargin.toFixed(4)),
    face_right_margin: Number(faceRightMargin.toFixed(4)),
    alignment_score: Number(alignmentScore.toFixed(4)),
    chin_to_forehead: Number(distance(chinPoint, foreheadPoint).toFixed(4)),
    hand_count: handCount,
    hand_near_face: handNearFace,
    quality_hint: qualityHint
  };
}

export function summarizeLandmarks(rawLandmarks: Point[] = []) {
  return rawLandmarks.map((point) => [
    Number(point.x.toFixed(6)),
    Number(point.y.toFixed(6)),
    Number((point.z ?? 0).toFixed(6))
  ]);
}

export function summarizeHands(rawHands: Point[][] = []) {
  return rawHands.map((hand) =>
    hand.map((point) => [
      Number(point.x.toFixed(6)),
      Number(point.y.toFixed(6)),
      Number((point.z ?? 0).toFixed(6))
    ])
  );
}
