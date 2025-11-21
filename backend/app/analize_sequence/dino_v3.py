"""
DINOv3 Feature Extractor for Surgical-Recap

手術動画のフレーム解析用DINOv3特徴抽出モジュール。
Tesla T4 (16GB)でのベンチマーク結果に基づき、解像度448を採用。

Benchmark (2024-11-21):
    Resolution 448 + Batch 64 = 63.9 fps, VRAM 1.18GB
"""

import sys
from pathlib import Path
from typing import List, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import torch
import torchvision.transforms as transforms
import numpy as np
from PIL import Image

# Add dinov3 directory to path
DINOV3_DIR = Path("/home/ubuntu/work/shibata/dinov3")
if str(DINOV3_DIR) not in sys.path:
    sys.path.insert(0, str(DINOV3_DIR))

from transformers import AutoModel, AutoImageProcessor

# Resolution config (based on benchmark 2024-11-21)
# 224: ~296 fps, 384: ~92 fps, 448: ~64 fps, 518: ~45 fps
DEFAULT_RESOLUTION = 448
DEFAULT_BATCH_SIZE = 64


class SurgicalDinoExtractor:
    """
    DINOv3 Feature Extractor for Surgical Video Analysis

    手術フレームから高品質な視覚特徴を抽出。
    バッチ処理による高速化、シーン変化検出をサポート。

    Example:
        extractor = SurgicalDinoExtractor()
        features = extractor.extract_features("frame.jpg")
        scene_changes = extractor.detect_scene_changes(frame_paths)
    """

    def __init__(
        self,
        device: Optional[str] = None,
        resolution: int = DEFAULT_RESOLUTION,
    ):
        """
        Initialize the surgical DINO extractor.

        Args:
            device: Device to use (default: auto-detect CUDA)
            resolution: Input image resolution (default: 448)
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.resolution = resolution

        print(f"🔧 Initializing Surgical DINO Extractor...")
        print(f"   Device: {self.device}")
        print(f"   Resolution: {self.resolution}")

        # Load DINOv3 model from HuggingFace
        model_path = str(DINOV3_DIR / "models" / "dinov3-vits16")
        self.model = AutoModel.from_pretrained(model_path)
        self.model = self.model.to(self.device).eval()
        self.processor = AutoImageProcessor.from_pretrained(model_path)

        # Custom transform for specified resolution
        self.transform = transforms.Compose([
            transforms.Resize(
                int(self.resolution * 1.1),
                interpolation=transforms.InterpolationMode.BICUBIC
            ),
            transforms.CenterCrop(self.resolution),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            ),
        ])

        print(f"✓ Model loaded on {self.device}")
        print(f"  Feature dimension: {self.model.config.hidden_size}")
        print(f"  Parameters: {sum(p.numel() for p in self.model.parameters()) / 1e6:.1f}M")
    
    def _load_image(self, image: Union[str, Path, Image.Image]) -> Image.Image:
        """Load image from path or return PIL Image."""
        if isinstance(image, (str, Path)):
            return Image.open(image).convert("RGB")
        return image.convert("RGB") if image.mode != "RGB" else image

    def extract_features(
        self,
        image: Union[str, Path, Image.Image],
        normalize: bool = True,
    ) -> torch.Tensor:
        """
        Extract features from a single image.

        Args:
            image: Input image (path or PIL Image)
            normalize: If True, normalize features to unit length

        Returns:
            Feature vector [1, 384]
        """
        img = self._load_image(image)
        tensor = self.transform(img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(tensor)
            features = outputs.last_hidden_state[:, 0]  # CLS token

        if normalize:
            features = features / features.norm(dim=-1, keepdim=True)

        return features

    def _load_and_transform(self, image: Union[str, Path, Image.Image]) -> torch.Tensor:
        """Load image and apply transform."""
        return self.transform(self._load_image(image))

    def extract_features_batch(
        self,
        images: List[Union[str, Path, Image.Image]],
        normalize: bool = True,
        batch_size: int = DEFAULT_BATCH_SIZE,
        num_workers: int = 4,
    ) -> torch.Tensor:
        """
        Extract features from multiple images in batches.

        Args:
            images: List of images (paths or PIL Images)
            normalize: If True, normalize features to unit length
            batch_size: Batch size for processing (default: 64)
            num_workers: Number of threads for parallel image loading (default: 4)

        Returns:
            Feature matrix [N, 384]
        """
        n_images = len(images)
        feature_dim = self.model.config.hidden_size

        # Pre-allocate output tensor on GPU
        all_features = torch.empty(
            (n_images, feature_dim),
            dtype=torch.float32,
            device=self.device
        )

        for i in range(0, n_images, batch_size):
            batch_images = images[i:i + batch_size]
            batch_end = min(i + batch_size, n_images)

            # Parallel image loading and transform
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                tensors = list(executor.map(self._load_and_transform, batch_images))

            batch_tensor = torch.stack(tensors).to(self.device)

            # Extract features
            with torch.no_grad():
                outputs = self.model(batch_tensor)
                features = outputs.last_hidden_state[:, 0]  # CLS token

                if normalize:
                    features = features / features.norm(dim=-1, keepdim=True)

                # Write directly to pre-allocated tensor
                all_features[i:batch_end] = features

        return all_features.cpu()
    
    def compute_similarity(
        self,
        image1: Union[str, Path, Image.Image],
        image2: Union[str, Path, Image.Image],
    ) -> float:
        """
        Compute cosine similarity between two images.
        
        Args:
            image1: First image
            image2: Second image
            
        Returns:
            Cosine similarity score [-1, 1]
        """
        features1 = self.extract_features(image1, normalize=True)
        features2 = self.extract_features(image2, normalize=True)
        
        similarity = torch.cosine_similarity(features1, features2, dim=-1)
        return similarity.item()
    
    def detect_scene_changes(
        self,
        frame_paths: List[Union[str, Path]],
        threshold: float = 0.7,
        normalize: bool = True,
    ) -> List[int]:
        """
        Detect scene changes in a sequence of frames.
        
        Args:
            frame_paths: List of frame paths in temporal order
            threshold: Similarity threshold (lower = more different)
            normalize: If True, normalize features
            
        Returns:
            List of frame indices where scene changes occur
        """
        print(f"🎬 Analyzing {len(frame_paths)} frames for scene changes...")
        
        # Extract features for all frames
        features = self.extract_features_batch(frame_paths, normalize=normalize)
        
        # Compare consecutive frames
        scene_changes = []
        for i in range(len(features) - 1):
            similarity = torch.cosine_similarity(
                features[i:i+1],
                features[i+1:i+2],
                dim=-1
            )
            
            if similarity.item() < threshold:
                scene_changes.append(i + 1)
                print(f"   Scene change at frame {i + 1} (similarity: {similarity.item():.4f})")
        
        print(f"✓ Found {len(scene_changes)} scene changes")
        return scene_changes
    
    def cluster_phases(
        self,
        frame_paths: List[Union[str, Path]],
        n_clusters: int = 5,
    ) -> np.ndarray:
        """
        Cluster frames into surgical phases.
        
        Args:
            frame_paths: List of frame paths
            n_clusters: Number of phases to identify
            
        Returns:
            Cluster assignments [N]
        """
        from sklearn.cluster import KMeans
        
        print(f"🔬 Clustering {len(frame_paths)} frames into {n_clusters} phases...")
        
        # Extract features
        features = self.extract_features_batch(frame_paths, normalize=True)
        features_np = features.cpu().numpy()
        
        # Cluster
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(features_np)
        
        # Show distribution
        unique, counts = np.unique(clusters, return_counts=True)
        print(f"\n   Phase distribution:")
        for phase, count in zip(unique, counts):
            print(f"      Phase {phase}: {count} frames ({count/len(clusters)*100:.1f}%)")
        
        return clusters
    
    def find_similar_frames(
        self,
        query_frame: Union[str, Path, Image.Image],
        database_frames: List[Union[str, Path]],
        top_k: int = 5,
    ) -> List[tuple]:
        """
        Find most similar frames to a query frame.
        
        Args:
            query_frame: Query frame
            database_frames: Database of frames to search
            top_k: Number of results to return
            
        Returns:
            List of (index, similarity_score) tuples
        """
        # Extract query features
        query_features = self.extract_features(query_frame, normalize=True)
        
        # Extract database features
        db_features = self.extract_features_batch(database_frames, normalize=True)
        
        # Compute similarities
        similarities = torch.cosine_similarity(
            query_features.expand(len(db_features), -1),
            db_features,
            dim=-1
        )
        
        # Get top-k
        top_k = min(top_k, len(similarities))
        top_scores, top_indices = torch.topk(similarities, top_k)
        
        results = [
            (idx.item(), score.item())
            for idx, score in zip(top_indices, top_scores)
        ]
        
        return results


def demo():
    """Demo the surgical DINO extractor"""
    print("=" * 80)
    print("Surgical-Recap DINOv3 Demo")
    print("=" * 80)
    
    # Create extractor
    extractor = SurgicalDinoExtractor()
    
    # Test with sample images
    sample_dir = Path("/home/ubuntu/work/shibata/dinov3/samples")
    sample_images = list(sample_dir.glob("*.jpg"))
    
    if len(sample_images) < 2:
        print("\n⚠️  Not enough sample images for demo")
        return
    
    print(f"\n📊 Found {len(sample_images)} sample images")
    
    # Test 1: Extract features
    print("\n1️⃣  Extracting features from a frame...")
    features = extractor.extract_features(sample_images[0])
    print(f"   ✓ Features shape: {features.shape}")
    print(f"   ✓ L2 norm: {features.norm().item():.6f}")
    
    # Test 2: Compute similarity
    if len(sample_images) >= 2:
        print("\n2️⃣  Computing similarity between frames...")
        similarity = extractor.compute_similarity(sample_images[0], sample_images[1])
        print(f"   ✓ Similarity: {similarity:.4f}")
    
    # Test 3: Batch processing
    print("\n3️⃣  Batch processing...")
    batch_features = extractor.extract_features_batch(sample_images[:min(5, len(sample_images))])
    print(f"   ✓ Batch features shape: {batch_features.shape}")
    
    # Test 4: Scene change detection
    if len(sample_images) >= 3:
        print("\n4️⃣  Detecting scene changes...")
        scene_changes = extractor.detect_scene_changes(sample_images[:min(5, len(sample_images))])
        print(f"   ✓ Found {len(scene_changes)} scene changes")
    
    # Test 5: Phase clustering
    if len(sample_images) >= 5:
        print("\n5️⃣  Clustering frames into phases...")
        clusters = extractor.cluster_phases(sample_images, n_clusters=min(3, len(sample_images)))
        print(f"   ✓ Clustering complete")
    
    # Test 6: Similar frame search
    if len(sample_images) >= 3:
        print("\n6️⃣  Finding similar frames...")
        results = extractor.find_similar_frames(
            sample_images[0],
            sample_images,
            top_k=3
        )
        print(f"   ✓ Top 3 similar frames:")
        for idx, score in results:
            print(f"      {sample_images[idx].name}: {score:.4f}")
    
    print("\n" + "=" * 80)
    print("✅ Demo complete! DINOv3 is ready for surgical video analysis!")
    print("=" * 80)
    
    print("\n💡 Usage in your code:")
    print("   from app.analize_sequence.dino_v3 import SurgicalDinoExtractor")
    print("   extractor = SurgicalDinoExtractor()")
    print("   features = extractor.extract_features(frame_path)")


if __name__ == "__main__":
    demo()
