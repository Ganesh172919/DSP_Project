"""
models/recognizer.py — LAYER 2: Face Recognition (ArcFace)

Uses ONNX Runtime to load the ArcFace recognition model directly —
NO insightface package required (avoids C++ compilation on Windows).

Model: w600k_r50.onnx (ResNet-50 trained on WebFace600K, 512-d embeddings)
Auto-downloads from insightface GitHub releases on first use.

Matching:  cosine similarity, threshold 0.4 (tunable)
Storage:   FAISS IndexFlatIP (inner product ≈ cosine on L2-normalized vectors)
Registration: capture 5 frames → average embedding → L2-normalize → store

Also includes:
  - Fine-tuning loop with ArcFace loss on custom identity data
  - ONNX export
  - INT8 quantization
  - Inference benchmark
"""

import logging
import os
import shutil
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import onnxruntime as ort

from app.config import (
    EMBEDDING_DIM, SIMILARITY_THRESHOLD,
    REGISTRATION_FRAMES, FAISS_INDEX_PATH, MODEL_DIR, DEVICE,
)

logger = logging.getLogger(__name__)

# ─── Model download config ──────────────────────────────────────────────
BUFFALO_L_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
ARCFACE_MODEL_NAME = "w600k_r50.onnx"


def _download_arcface_model(model_dir: Path) -> Path:
    """
    Download the ArcFace ONNX model from insightface's GitHub releases.
    Extracts only w600k_r50.onnx (~167 MB) from the buffalo_l pack.
    """
    model_path = model_dir / ARCFACE_MODEL_NAME
    if model_path.exists():
        return model_path

    model_dir.mkdir(parents=True, exist_ok=True)
    zip_path = model_dir / "buffalo_l.zip"

    logger.info(f"Downloading ArcFace model from {BUFFALO_L_URL} ...")
    logger.info("This is a one-time download (~329 MB). Please wait...")

    try:
        # Download with progress
        def _progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 // total_size)
                mb = downloaded / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                print(f"\r  Downloading: {mb:.0f}/{total_mb:.0f} MB ({pct}%)", end="", flush=True)

        urllib.request.urlretrieve(str(BUFFALO_L_URL), str(zip_path), reporthook=_progress)
        print()  # newline after progress

        # Extract only the recognition model
        logger.info("Extracting ArcFace model from zip...")
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            for name in zf.namelist():
                if os.path.basename(name) == ARCFACE_MODEL_NAME:
                    with zf.open(name) as src, open(str(model_path), "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    logger.info(f"Extracted {ARCFACE_MODEL_NAME} to {model_path}")
                    break
            else:
                raise FileNotFoundError(f"{ARCFACE_MODEL_NAME} not found in zip archive")

        # Clean up zip
        zip_path.unlink(missing_ok=True)
        return model_path

    except Exception as e:
        zip_path.unlink(missing_ok=True)
        logger.error(f"Failed to download ArcFace model: {e}")
        raise RuntimeError(
            f"Could not download ArcFace model.\n"
            f"Please download manually from:\n  {BUFFALO_L_URL}\n"
            f"Extract '{ARCFACE_MODEL_NAME}' to:\n  {model_dir}\n"
            f"Original error: {e}"
        )


@dataclass
class RecognitionResult:
    embedding: np.ndarray          # 512-d L2-normalized
    matched_user_id: Optional[str] = None
    similarity: float = 0.0
    match_found: bool = False


class FaceRecognizer:
    """
    Layer 2 — ArcFace 512-d embedding extraction via ONNX Runtime
    + FAISS nearest-neighbor matching.
    """

    def __init__(self):
        self.session: Optional[ort.InferenceSession] = None
        self.input_name: str = ""
        self.faiss_index = None
        self.user_id_map: dict[int, str] = {}  # FAISS row → user_id
        self._initialized = False

    def _lazy_init(self):
        if self._initialized:
            return

        import faiss

        # Download model if not present
        model_path = _download_arcface_model(MODEL_DIR)

        # Load ONNX model with appropriate execution provider
        providers = ["CPUExecutionProvider"]
        if DEVICE == "cuda":
            providers.insert(0, "CUDAExecutionProvider")

        self.session = ort.InferenceSession(str(model_path), providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        logger.info(f"ArcFace ONNX model loaded: {model_path.name}  "
                     f"input={self.input_name}  providers={self.session.get_providers()}")

        # Initialize FAISS index
        self.faiss_index = faiss.IndexFlatIP(EMBEDDING_DIM)

        # Load persisted index if exists
        if FAISS_INDEX_PATH.exists():
            self.faiss_index = faiss.read_index(str(FAISS_INDEX_PATH))
            logger.info(f"Loaded FAISS index with {self.faiss_index.ntotal} vectors")

        self._initialized = True

    def _preprocess(self, aligned_face: np.ndarray) -> np.ndarray:
        """
        Preprocess a 112×112 BGR face for ArcFace inference.

        Steps:
          1. BGR → RGB
          2. Normalize to [-1, 1]:  (pixel - 127.5) / 127.5
          3. Transpose HWC → CHW
          4. Add batch dimension

        Returns: float32 array of shape [1, 3, 112, 112]
        """
        img = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32)
        img = (img - 127.5) / 127.5           # normalize to [-1, 1]
        img = np.transpose(img, (2, 0, 1))    # HWC → CHW
        img = np.expand_dims(img, axis=0)      # [1, 3, 112, 112]
        return img

    def extract_embedding(self, aligned_face: np.ndarray) -> np.ndarray:
        """
        Extract 512-d L2-normalized embedding from a 112×112 aligned face.

        Args:
            aligned_face: BGR numpy array, 112×112

        Returns: 512-d float32 vector, L2-normalized
        """
        self._lazy_init()

        blob = self._preprocess(aligned_face)
        outputs = self.session.run(None, {self.input_name: blob})
        embedding = outputs[0][0].astype(np.float32)

        # L2-normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def compute_template(self, aligned_faces: list[np.ndarray]) -> np.ndarray:
        """
        Compute averaged + L2-normalized template from multiple face crops.
        Used during registration (5 frames → 1 template).
        """
        embeddings = [self.extract_embedding(face) for face in aligned_faces]
        avg_embedding = np.mean(embeddings, axis=0).astype(np.float32)

        # L2-normalize the average
        norm = np.linalg.norm(avg_embedding)
        if norm > 0:
            avg_embedding = avg_embedding / norm

        return avg_embedding

    def register(self, user_id: str, template: np.ndarray):
        """Add a user's template to the FAISS index."""
        self._lazy_init()
        import faiss

        idx = self.faiss_index.ntotal
        self.faiss_index.add(template.reshape(1, -1))
        self.user_id_map[idx] = user_id

        # Persist index
        faiss.write_index(self.faiss_index, str(FAISS_INDEX_PATH))
        logger.info(f"Registered user '{user_id}' at FAISS index {idx}")

    def match(self, embedding: np.ndarray, threshold: float = None) -> RecognitionResult:
        """
        Find the closest match in the FAISS index.

        Returns: RecognitionResult with similarity and matched user_id
        """
        self._lazy_init()

        if threshold is None:
            threshold = SIMILARITY_THRESHOLD

        if self.faiss_index.ntotal == 0:
            return RecognitionResult(embedding=embedding)

        # Search top-1
        scores, indices = self.faiss_index.search(embedding.reshape(1, -1), 1)
        similarity = float(scores[0][0])
        idx = int(indices[0][0])

        if similarity >= threshold and idx in self.user_id_map:
            return RecognitionResult(
                embedding=embedding,
                matched_user_id=self.user_id_map[idx],
                similarity=similarity,
                match_found=True,
            )

        return RecognitionResult(embedding=embedding, similarity=similarity)

    def match_against_template(
        self, embedding: np.ndarray, template: np.ndarray, threshold: float = None
    ) -> RecognitionResult:
        """
        Direct cosine similarity between two embeddings (no FAISS).
        Used for authentication against a specific user's stored template.
        """
        if threshold is None:
            threshold = SIMILARITY_THRESHOLD

        similarity = float(np.dot(embedding, template))

        return RecognitionResult(
            embedding=embedding,
            similarity=similarity,
            match_found=similarity >= threshold,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Fine-tuning with ArcFace Loss (training code)
# ═══════════════════════════════════════════════════════════════════════════

def arcface_training_loop():
    """
    Full training loop: fine-tune IResNet on custom identity data with ArcFace loss.
    This is reference code — adapt paths and hyperparameters for your dataset.
    """
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset
    from torchvision import transforms
    import math

    # ─── ArcFace Loss Implementation ────────────────────────────────────

    class ArcFaceLoss(nn.Module):
        """
        Additive Angular Margin Loss (ArcFace).
        Pushes intra-class embeddings closer and inter-class embeddings apart
        in angular space.
        """
        def __init__(self, embedding_dim: int, num_classes: int,
                     s: float = 64.0, m: float = 0.5):
            super().__init__()
            self.s = s       # scale factor
            self.m = m       # angular margin
            self.weight = nn.Parameter(torch.FloatTensor(num_classes, embedding_dim))
            nn.init.xavier_uniform_(self.weight)
            self.cos_m = math.cos(m)
            self.sin_m = math.sin(m)
            self.th = math.cos(math.pi - m)     # threshold
            self.mm = math.sin(math.pi - m) * m  # penalty term

        def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
            # Normalize weights and embeddings
            cosine = torch.nn.functional.linear(
                torch.nn.functional.normalize(embeddings),
                torch.nn.functional.normalize(self.weight),
            )
            sine = torch.sqrt(1.0 - torch.clamp(cosine ** 2, 0, 1))

            # cos(θ + m) = cos(θ)cos(m) - sin(θ)sin(m)
            phi = cosine * self.cos_m - sine * self.sin_m
            phi = torch.where(cosine > self.th, phi, cosine - self.mm)

            # One-hot encoding
            one_hot = torch.zeros_like(cosine)
            one_hot.scatter_(1, labels.view(-1, 1).long(), 1)

            output = (one_hot * phi) + ((1.0 - one_hot) * cosine)
            output *= self.s

            return nn.CrossEntropyLoss()(output, labels)

    # ─── Simple Face Dataset ────────────────────────────────────────────

    class FaceDataset(Dataset):
        """
        Expects directory structure:
            data_root/
                person_001/
                    img_001.jpg
                    img_002.jpg
                person_002/
                    ...
        """
        def __init__(self, data_root: str, transform=None):
            self.samples = []
            self.labels = []
            self.transform = transform
            self.class_names = []

            root = Path(data_root)
            for cls_idx, person_dir in enumerate(sorted(root.iterdir())):
                if not person_dir.is_dir():
                    continue
                self.class_names.append(person_dir.name)
                for img_path in person_dir.glob("*.jpg"):
                    self.samples.append(str(img_path))
                    self.labels.append(cls_idx)

            logger.info(f"Loaded {len(self.samples)} images, {len(self.class_names)} identities")

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            img = cv2.imread(self.samples[idx])
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (112, 112))
            if self.transform:
                img = self.transform(img)
            return img, self.labels[idx]

    # ─── Training ───────────────────────────────────────────────────────

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data_root = "data/faces"  # change to your dataset path
    num_epochs = 20
    batch_size = 32    # increase to 128+ on GPU
    lr = 1e-3

    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])

    dataset = FaceDataset(data_root, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=2)

    # IResNet-100 backbone (simplified version for fine-tuning)
    from torchvision.models import resnet50
    backbone = resnet50(weights=None)
    backbone.fc = nn.Linear(2048, EMBEDDING_DIM)
    backbone = backbone.to(device)

    arcface_loss = ArcFaceLoss(EMBEDDING_DIM, len(dataset.class_names)).to(device)

    optimizer = optim.Adam(
        list(backbone.parameters()) + list(arcface_loss.parameters()),
        lr=lr, weight_decay=1e-4,
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)

    best_loss = float("inf")
    for epoch in range(num_epochs):
        backbone.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for batch_idx, (images, labels) in enumerate(dataloader):
            images = images.to(device)
            labels = labels.to(device)

            embeddings = backbone(images)
            loss = arcface_loss(embeddings, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            total += labels.size(0)

            # Track accuracy using cosine similarity to class centers
            with torch.no_grad():
                normed_emb = torch.nn.functional.normalize(embeddings)
                normed_w = torch.nn.functional.normalize(arcface_loss.weight)
                cos_sim = torch.mm(normed_emb, normed_w.t())
                predicted = cos_sim.argmax(dim=1)
                correct += (predicted == labels).sum().item()

        epoch_loss = running_loss / len(dataloader)
        epoch_acc = correct / total * 100
        scheduler.step()

        print(f"Epoch [{epoch+1}/{num_epochs}] Loss: {epoch_loss:.4f}  Acc: {epoch_acc:.1f}%")

        if epoch_loss < best_loss:
            best_loss = epoch_loss
            torch.save(backbone.state_dict(), "weights/arcface_finetuned.pth")
            print(f"  → Saved best model (loss={best_loss:.4f})")

    print("Training complete.")


# ═══════════════════════════════════════════════════════════════════════════
# ONNX Export
# ═══════════════════════════════════════════════════════════════════════════

def export_to_onnx():
    """Export the fine-tuned backbone to ONNX format."""
    import torch
    from torchvision.models import resnet50

    device = torch.device("cpu")
    backbone = resnet50(weights=None)
    backbone.fc = torch.nn.Linear(2048, EMBEDDING_DIM)
    backbone.load_state_dict(torch.load("weights/arcface_finetuned.pth", map_location=device))
    backbone.eval()

    dummy_input = torch.randn(1, 3, 112, 112)
    torch.onnx.export(
        backbone, dummy_input, "weights/arcface.onnx",
        input_names=["face"],
        output_names=["embedding"],
        dynamic_axes={"face": {0: "batch"}, "embedding": {0: "batch"}},
        opset_version=17,
    )
    print("Exported to weights/arcface.onnx")


# ═══════════════════════════════════════════════════════════════════════════
# INT8 Quantization
# ═══════════════════════════════════════════════════════════════════════════

def quantize_int8():
    """Post-training static INT8 quantization via ONNX Runtime."""
    from onnxruntime.quantization import quantize_static, CalibrationDataReader

    class FaceCalibrationReader(CalibrationDataReader):
        def __init__(self, calib_dir: str = "data/calibration", count: int = 100):
            self.data = []
            calib_path = Path(calib_dir)
            if calib_path.exists():
                for img_path in list(calib_path.glob("*.jpg"))[:count]:
                    img = cv2.imread(str(img_path))
                    img = cv2.resize(img, (112, 112))
                    img = img.astype(np.float32) / 255.0
                    img = (img - 0.5) / 0.5
                    img = np.transpose(img, (2, 0, 1))[np.newaxis, ...]
                    self.data.append({"face": img})
            else:
                # Generate random calibration data if no images available
                for _ in range(count):
                    self.data.append({"face": np.random.randn(1, 3, 112, 112).astype(np.float32)})
            self.idx = 0

        def get_next(self):
            if self.idx >= len(self.data):
                return None
            result = self.data[self.idx]
            self.idx += 1
            return result

    quantize_static(
        "weights/arcface.onnx",
        "weights/arcface_int8.onnx",
        FaceCalibrationReader(),
    )
    print("Quantized to weights/arcface_int8.onnx")


# ═══════════════════════════════════════════════════════════════════════════
# Benchmark
# ═══════════════════════════════════════════════════════════════════════════

def benchmark(num_runs: int = 100):
    """Benchmark inference speed (ms/frame) on CPU."""
    recognizer = FaceRecognizer()
    dummy_face = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)

    # Warmup
    for _ in range(5):
        recognizer.extract_embedding(dummy_face)

    times = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        recognizer.extract_embedding(dummy_face)
        times.append((time.perf_counter() - t0) * 1000)

    times = np.array(times)
    print(f"ArcFace Embedding Benchmark ({num_runs} runs):")
    print(f"  Mean:   {times.mean():.2f} ms")
    print(f"  Median: {np.median(times):.2f} ms")
    print(f"  P95:    {np.percentile(times, 95):.2f} ms")
    print(f"  P99:    {np.percentile(times, 99):.2f} ms")


if __name__ == "__main__":
    import sys
    if "--train" in sys.argv:
        arcface_training_loop()
    elif "--export" in sys.argv:
        export_to_onnx()
    elif "--quantize" in sys.argv:
        quantize_int8()
    elif "--benchmark" in sys.argv:
        benchmark()
    else:
        print("Usage: python recognizer.py [--train|--export|--quantize|--benchmark]")
        print("Running benchmark by default...")
        benchmark()
