const slides = [
  {
    title: "Opening",
    section: "Overview",
    note: "Open by explaining that the project is not only face recognition. It is a layered authentication system that verifies face presence, identity, liveness, synthetic-media risk, optional challenge response, and optional VLM reasoning."
  },
  {
    title: "System Flow",
    section: "Flow",
    note: "Walk left to right. Browser camera data becomes multipart form data, then FastAPI decodes it, the pipeline runs model layers, the decision is logged, and the frontend displays scores and the final decision."
  },
  {
    title: "Registration",
    section: "Enrollment",
    note: "Registration builds a stable template from multiple frames. The system does not save a raw face embedding without protection; it encrypts the normalized ArcFace template with AES-256-GCM before storing it."
  },
  {
    title: "Model Roles",
    section: "AI Stack",
    note: "Each model is a specialist. YuNet finds a usable face, ArcFace verifies identity, liveness checks real-person evidence, deepfake detection checks manipulation, MediaPipe verifies fresh actions, and VLM adds explanation."
  },
  {
    title: "Identity",
    section: "YuNet + ArcFace",
    note: "YuNet produces landmarks and alignment. ArcFace converts the aligned face into a 512-dimensional embedding. Similarity is a cosine-style dot product against the stored encrypted template after decryption."
  },
  {
    title: "Liveness",
    section: "Anti-spoofing",
    note: "Liveness is a fusion problem. The system uses CNN features, texture, color, moire, movement, micro-movement, rPPG, and optional challenge scores. This is why video is stronger than a still image."
  },
  {
    title: "Deepfake",
    section: "Synthetic Risk",
    note: "The deepfake detector looks for artifacts from generated or swapped faces. It combines spectral, CNN, boundary, reflection, skin, color, and temporal signals into a probability."
  },
  {
    title: "Challenges",
    section: "Active Liveness",
    note: "Active challenge verification makes replay attacks harder because the requested action is fresh. MediaPipe FaceMesh and Hands provide the landmark evidence."
  },
  {
    title: "VLM",
    section: "Reasoning",
    note: "The VLM layer is optional. It runs after a traditional grant, compares registration and authentication frames, and returns same-person, liveness, authenticity, reasoning, and red flags."
  },
  {
    title: "Decision Gates",
    section: "Decision",
    note: "The final decision is deterministic once scores exist. Any required gate can deny. Only a valid face, sufficient liveness, low deepfake risk, passed instructions, and identity match produce a grant."
  },
  {
    title: "Threat Simulator",
    section: "Scenarios",
    note: "Use the simulator to show why multiple layers matter. A printed photo may match identity but fail liveness. A deepfake may pass basic identity but trigger synthetic risk."
  },
  {
    title: "Security",
    section: "Storage",
    note: "Close with security controls: encrypted biometric templates, JWT on grant, SQLite audit logging, threat flags, and future work such as encrypted VLM frames and production key management."
  }
];

const pipelineSteps = [
  ["Capture", "Browser camera captures frames or video through React pages."],
  ["Upload", "Axios sends multipart form data through the Vite proxy."],
  ["FastAPI", "Routes validate users, decode media, and call the pipeline."],
  ["YuNet", "Face detection, landmarks, pose checks, and alignment."],
  ["ArcFace", "512-dimensional identity embedding and cosine similarity."],
  ["Liveness", "CNN, texture, color, moire, motion, micro-movement, and rPPG."],
  ["Deepfake", "FFT, EfficientNet, boundary, reflection, texture, color, flicker."],
  ["Decision", "Threshold gates produce GRANT or DENY with reason and flags."],
  ["Storage", "Encrypted embeddings, auth logs, challenge logs, VLM metadata."],
  ["Response", "Frontend displays confidence, scores, reasoning, and JWT if granted."]
];

const modelCards = [
  {
    tag: "Layer 0",
    name: "Anti-Injection Guard",
    body: "Checks camera source metadata, virtual driver signatures, PRNU-like variance, and frame heuristics when a live camera handle is available."
  },
  {
    tag: "Layer 1",
    name: "OpenCV YuNet",
    body: "Detects the face, returns five landmarks, validates confidence and pose, then aligns the crop to ArcFace geometry."
  },
  {
    tag: "Layer 2",
    name: "ArcFace ONNX",
    body: "Generates a normalized 512-dimensional identity embedding and compares it against the stored encrypted template."
  },
  {
    tag: "Layer 3",
    name: "Liveness Fusion",
    body: "Uses MobileNetV3 features, texture, color, moire, optical flow, micro-movement, rPPG, and challenge scores."
  },
  {
    tag: "Layer 4",
    name: "Deepfake Detector",
    body: "Combines FFT spectral analysis, EfficientNet-B0 features, boundary artifacts, eye reflections, skin texture, color, and flicker."
  },
  {
    tag: "Layer 5",
    name: "MediaPipe Challenge",
    body: "Verifies fresh face and hand instructions with FaceMesh and Hands landmarks, reducing replay risk."
  },
  {
    tag: "Optional",
    name: "VLM Reasoner",
    body: "Uses Qwen or moondream to compare reference and authentication frames and return explainable identity, liveness, and authenticity judgments."
  },
  {
    tag: "Security",
    name: "AES + JWT + Logs",
    body: "Encrypts biometric templates, returns RS256 JWTs on grant, and writes auditable authentication history."
  }
];

const decisionGates = [
  ["Camera source", "Physical camera evidence when available", 100, "pass"],
  ["Face detection", "YuNet confidence >= 0.70 with acceptable pose", 92, "pass"],
  ["Liveness", "Fused liveness score >= 0.70", 84, "pass"],
  ["Deepfake", "Synthetic probability <= 0.30", 22, "pass"],
  ["Challenge", "Fresh instruction confidence >= 0.60 when required", 76, "pass"],
  ["Identity", "ArcFace similarity >= 0.40", 81, "pass"],
  ["Final", "All required gates pass, issue JWT", 95, "pass"]
];

const scenarios = [
  {
    id: "live",
    label: "Live user",
    decision: "GRANT",
    scores: {
      Face: 84,
      Liveness: 88,
      Deepfake: 8,
      Challenge: 80,
      VLM: 86
    }
  },
  {
    id: "photo",
    label: "Printed photo",
    decision: "DENY liveness_fail",
    scores: {
      Face: 72,
      Liveness: 24,
      Deepfake: 18,
      Challenge: 10,
      VLM: 38
    }
  },
  {
    id: "screen",
    label: "Screen replay",
    decision: "DENY liveness_fail",
    scores: {
      Face: 76,
      Liveness: 42,
      Deepfake: 31,
      Challenge: 22,
      VLM: 44
    }
  },
  {
    id: "deepfake",
    label: "Deepfake",
    decision: "DENY synthetic_face",
    scores: {
      Face: 79,
      Liveness: 71,
      Deepfake: 67,
      Challenge: 55,
      VLM: 36
    }
  }
];

let currentSlide = 0;
let activeScenario = scenarios[0];
let pipelineTimer = null;

const slideEls = Array.from(document.querySelectorAll(".slide"));
const menu = document.getElementById("slideMenu");
const counter = document.getElementById("slideCounter");
const progressFill = document.getElementById("progressFill");
const sectionLabel = document.getElementById("sectionLabel");
const motionLabel = document.getElementById("motionLabel");
const notes = document.getElementById("speakerNotes");

function buildMenu() {
  menu.innerHTML = "";
  slides.forEach((slide, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.innerHTML = `<strong>${index + 1}. ${slide.title}</strong><span>${slide.section}</span>`;
    button.addEventListener("click", () => goToSlide(index));
    menu.appendChild(button);
  });
}

function buildPipeline() {
  const root = document.getElementById("pipelineMap");
  if (!root) return;
  root.innerHTML = "";
  pipelineSteps.forEach(([title, body], index) => {
    const node = document.createElement("div");
    node.className = "pipeline-node";
    node.dataset.step = String(index);
    node.innerHTML = `<strong>${title}</strong><span>${body}</span>`;
    root.appendChild(node);
  });
}

function animatePipeline() {
  clearInterval(pipelineTimer);
  const nodes = Array.from(document.querySelectorAll(".pipeline-node"));
  nodes.forEach(node => node.classList.remove("active"));
  if (!nodes.length) return;
  let index = 0;
  nodes[index].classList.add("active");
  pipelineTimer = setInterval(() => {
    nodes.forEach(node => node.classList.remove("active"));
    index = (index + 1) % nodes.length;
    nodes[index].classList.add("active");
  }, 850);
}

function buildFrameStrip() {
  const root = document.getElementById("frameStrip");
  if (!root) return;
  root.innerHTML = "";
  for (let i = 0; i < 5; i += 1) {
    const frame = document.createElement("div");
    frame.className = "capture-frame";
    root.appendChild(frame);
  }
}

function buildEmbeddingBars() {
  const root = document.getElementById("embeddingBars");
  if (!root) return;
  root.innerHTML = "";
  for (let i = 0; i < 32; i += 1) {
    const bar = document.createElement("span");
    const height = 18 + Math.round((Math.sin(i * 1.7) + 1) * 38) + (i % 5) * 4;
    bar.style.height = `${height}px`;
    bar.style.animationDelay = `${i * 28}ms`;
    root.appendChild(bar);
  }
}

function buildModelBoard() {
  const root = document.getElementById("modelBoard");
  if (!root) return;
  root.innerHTML = "";
  modelCards.forEach(card => {
    const el = document.createElement("section");
    el.className = "model-card";
    el.innerHTML = `<span class="tag">${card.tag}</span><h3>${card.name}</h3><p>${card.body}</p>`;
    root.appendChild(el);
  });
}

function buildEmbeddingSpace() {
  const root = document.getElementById("embeddingSpace");
  if (!root) return;
  root.innerHTML = "";
  const points = [
    [30, 42, false],
    [34, 48, false],
    [39, 38, false],
    [46, 44, false],
    [75, 68, true],
    [81, 61, true],
    [68, 78, true]
  ];
  points.forEach(([x, y, impostor], index) => {
    const dot = document.createElement("span");
    dot.className = `embedding-dot${impostor ? " impostor" : ""}`;
    dot.style.left = `${x}%`;
    dot.style.top = `${y}%`;
    dot.style.animationDelay = `${index * 120}ms`;
    root.appendChild(dot);
  });
}

function buildPulseChart() {
  const root = document.getElementById("pulseChart");
  if (!root) return;
  root.innerHTML = "";
  for (let i = 0; i < 72; i += 1) {
    const point = document.createElement("span");
    point.className = "pulse-point";
    const x = (i / 71) * 100;
    const y = 50 - Math.sin(i * 0.42) * 24 - Math.sin(i * 0.11) * 8;
    point.style.left = `${x}%`;
    point.style.top = `${y}%`;
    root.appendChild(point);
  }
}

function drawRadar() {
  const canvas = document.getElementById("radarCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2 + 12;
  const radius = 145;
  const axes = [
    "FFT",
    "CNN",
    "Boundary",
    "Eyes",
    "Skin",
    "Color",
    "Flicker"
  ];
  const values = [0.22, 0.18, 0.14, 0.12, 0.19, 0.16, 0.09];

  ctx.clearRect(0, 0, w, h);
  ctx.lineWidth = 1;
  ctx.strokeStyle = "#d9dfd3";
  ctx.fillStyle = "#20231f";
  ctx.font = "14px system-ui";

  for (let ring = 1; ring <= 4; ring += 1) {
    ctx.beginPath();
    axes.forEach((axis, index) => {
      const angle = -Math.PI / 2 + (index / axes.length) * Math.PI * 2;
      const r = (radius / 4) * ring;
      const x = cx + Math.cos(angle) * r;
      const y = cy + Math.sin(angle) * r;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.stroke();
  }

  axes.forEach((axis, index) => {
    const angle = -Math.PI / 2 + (index / axes.length) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
    ctx.stroke();
    ctx.fillText(axis, cx + Math.cos(angle) * (radius + 24) - 24, cy + Math.sin(angle) * (radius + 24));
  });

  ctx.beginPath();
  values.forEach((value, index) => {
    const angle = -Math.PI / 2 + (index / values.length) * Math.PI * 2;
    const r = value * radius;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.fillStyle = "rgba(24, 138, 98, 0.26)";
  ctx.strokeStyle = "#188a62";
  ctx.lineWidth = 3;
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = "#20231f";
  ctx.font = "bold 18px system-ui";
  ctx.fillText("Deepfake probability: 0.18", 146, 38);
}

function buildMiniFrames() {
  ["refFrames", "authFrames"].forEach(id => {
    const root = document.getElementById(id);
    if (!root) return;
    root.innerHTML = "";
    for (let i = 0; i < 3; i += 1) {
      const frame = document.createElement("div");
      frame.className = "mini-frame";
      root.appendChild(frame);
    }
  });
}

function buildDecisionGates() {
  const root = document.getElementById("decisionGates");
  if (!root) return;
  root.innerHTML = "";
  decisionGates.forEach(([name, body, score, state]) => {
    const row = document.createElement("div");
    row.className = `gate-row ${state}`;
    row.innerHTML = `
      <strong>${name}</strong>
      <div>
        <div>${body}</div>
        <div class="gate-bar"><span style="width:${score}%"></span></div>
      </div>
      <strong>${score}%</strong>
    `;
    root.appendChild(row);
  });
}

function buildScenarioButtons() {
  const root = document.getElementById("scenarioButtons");
  if (!root) return;
  root.innerHTML = "";
  scenarios.forEach(scenario => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = scenario.label;
    button.dataset.id = scenario.id;
    button.addEventListener("click", () => {
      activeScenario = scenario;
      updateScenario();
    });
    root.appendChild(button);
  });
}

function updateScenario() {
  const buttons = Array.from(document.querySelectorAll("#scenarioButtons button"));
  buttons.forEach(button => {
    button.classList.toggle("active", button.dataset.id === activeScenario.id);
  });

  const root = document.getElementById("scoreDashboard");
  if (!root) return;
  root.innerHTML = "";

  Object.entries(activeScenario.scores).forEach(([name, value]) => {
    const inverted = name === "Deepfake";
    const bad = inverted ? value > 30 : value < 60;
    const line = document.createElement("div");
    line.className = "score-line";
    line.innerHTML = `
      <strong>${name}</strong>
      <div class="score-track"><span class="${bad ? "bad" : ""}" style="width:${value}%"></span></div>
      <strong>${value}%</strong>
    `;
    root.appendChild(line);
  });

  const decision = document.createElement("div");
  decision.className = "score-line";
  decision.innerHTML = `<strong>Decision</strong><div>${activeScenario.decision}</div><strong>${activeScenario.id === "live" ? "OK" : "STOP"}</strong>`;
  root.appendChild(decision);
}

function updateSlideUI() {
  slideEls.forEach((slide, index) => {
    slide.classList.toggle("active", index === currentSlide);
  });

  Array.from(menu.children).forEach((button, index) => {
    button.classList.toggle("active", index === currentSlide);
  });

  const slide = slides[currentSlide];
  counter.textContent = `${currentSlide + 1} / ${slides.length}`;
  progressFill.style.width = `${((currentSlide + 1) / slides.length) * 100}%`;
  sectionLabel.textContent = slide.section;
  motionLabel.textContent = `Slide ${currentSlide + 1} animation`;
  notes.textContent = slide.note;

  if (currentSlide === 1) animatePipeline();
  else clearInterval(pipelineTimer);

  if (currentSlide === 6) drawRadar();
}

function goToSlide(index) {
  currentSlide = Math.max(0, Math.min(slides.length - 1, index));
  updateSlideUI();
}

function nextSlide() {
  goToSlide((currentSlide + 1) % slides.length);
}

function prevSlide() {
  goToSlide((currentSlide - 1 + slides.length) % slides.length);
}

function replaySlide() {
  const active = slideEls[currentSlide];
  active.classList.remove("replay");
  void active.offsetWidth;
  active.classList.add("replay");
  if (currentSlide === 1) animatePipeline();
  if (currentSlide === 6) drawRadar();
}

function bindControls() {
  document.getElementById("nextBtn").addEventListener("click", nextSlide);
  document.getElementById("prevBtn").addEventListener("click", prevSlide);
  document.getElementById("replayBtn").addEventListener("click", replaySlide);

  window.addEventListener("keydown", event => {
    if (event.key === "ArrowRight" || event.key === " ") {
      event.preventDefault();
      nextSlide();
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      prevSlide();
    }
    if (event.key.toLowerCase() === "r") {
      replaySlide();
    }
    const numeric = Number(event.key);
    if (numeric >= 1 && numeric <= 9) {
      goToSlide(numeric - 1);
    }
  });
}

function animateChallengePrompt() {
  const prompt = document.getElementById("challengePrompt");
  if (!prompt) return;
  const prompts = [
    "Blink twice",
    "Turn head left",
    "Show open palm",
    "Smile",
    "Wave hand"
  ];
  let index = 0;
  setInterval(() => {
    index = (index + 1) % prompts.length;
    prompt.textContent = prompts[index];
  }, 2200);
}

function rotateVlmReasoning() {
  const node = document.getElementById("vlmReasoning");
  if (!node) return;
  const lines = [
    "Same person, live texture, no visible spoof artifacts.",
    "Face structure is consistent across registration and login frames.",
    "Authentication frames show natural lighting and skin variation.",
    "No obvious screen edge, paper texture, or mask boundary is visible."
  ];
  let index = 0;
  setInterval(() => {
    index = (index + 1) % lines.length;
    node.textContent = lines[index];
  }, 2600);
}

function init() {
  buildMenu();
  buildPipeline();
  buildFrameStrip();
  buildEmbeddingBars();
  buildModelBoard();
  buildEmbeddingSpace();
  buildPulseChart();
  buildMiniFrames();
  buildDecisionGates();
  buildScenarioButtons();
  updateScenario();
  bindControls();
  animateChallengePrompt();
  rotateVlmReasoning();
  updateSlideUI();
}

init();

