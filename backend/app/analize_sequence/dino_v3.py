"""
DINOv3 Feature Extractor for Surgical-Recap

This module provides DINOv3 feature extraction for surgical video analysis.
It uses the unified DINO interface from the dinov3 repository.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Union
import torch
import numpy as np
from PIL import Image

# Add dinov3 directory to path
DINOV3_DIR = Path("/home/ubuntu/work/shibata/dinov3")
if str(DINOV3_DIR) not in sys.path:
    sys.path.insert(0, str(DINOV3_DIR))

from surgical_recap_integration import get_default_extractor
from dino_extractor import DinoFeatureExtractor


class SurgicalDinoExtractor:
    """
    DINOv3 Feature Extractor for Surgical Video Analysis
    
    Features:
    - Extracts high-quality visual features from surgical frames
    - Supports both DINOv2 (development) and DINOv3 (production)
    - Batch processing for efficiency
    - Scene change detection
    - Frame similarity computation
    
    Example:
        # Create extractor
        extractor = SurgicalDinoExtractor(use_dinov3=True)
        
        # Extract features from a frame
        features = extractor.extract_features("frame.jpg")
        
        # Detect scene changes
        scene_changes = extractor.detect_scene_changes(frame_paths)
    """
    
    def __init__(
        self,
        use_dinov3: bool = True,
        device: Optional[str] = None,
    ):
        """
        Initialize the surgical DINO extractor.
        
        Args:
            use_dinov3: If True, use DINOv3 (recommended for production)
            device: Device to use (default: auto-detect CUDA)
        """
        self.use_dinov3 = use_dinov3
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        print(f"🔧 Initializing Surgical DINO Extractor...")
        print(f"   Model: {'DINOv3' if use_dinov3 else 'DINOv2'}")
        print(f"   Device: {self.device}")
        
        # Get the appropriate extractor
        if use_dinov3:
            self.extractor = get_default_extractor(
                use_dinov3=True,
                hf_model_path=str(DINOV3_DIR / "models" / "dinov3-vits16")
            )
        else:
            self.extractor = get_default_extractor(use_dinov3=False)
        
        info = self.extractor.get_info()
        print(f"✓ Model loaded: {info['model_name']}")
        print(f"  Feature dimension: {info['feature_dim']}")
        print(f"  Parameters: {info['num_parameters'] / 1e6:.1f}M")
    
    def extract_features(
        self,
        image: Union[str, Path, Image.Image, torch.Tensor],
        normalize: bool = True,
    ) -> torch.Tensor:
        """
        Extract features from a single image.
        
        Args:
            image: Input image (path, PIL Image, or tensor)
            normalize: If True, normalize features to unit length
            
        Returns:
            Feature vector [1, 384]
        """
        features = self.extractor(image)
        
        if normalize:
            features = features / features.norm(dim=-1, keepdim=True)
        
        return features
    
    def extract_features_batch(
        self,
        images: List[Union[str, Path, Image.Image]],
        normalize: bool = True,
        batch_size: int = 32,
    ) -> torch.Tensor:
        """
        Extract features from multiple images in batches.
        
        Args:
            images: List of images (paths or PIL Images)
            normalize: If True, normalize features to unit length
            batch_size: Batch size for processing
            
        Returns:
            Feature matrix [N, 384]
        """
        all_features = []
        
        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            
            # Preprocess batch
            if self.extractor._is_hf_model:
                # HF model expects dict
                batch_tensors = [self.extractor.preprocess(img)['pixel_values'] for img in batch]
            else:
                batch_tensors = [self.extractor.preprocess(img) for img in batch]
            
            batch_tensor = torch.cat(batch_tensors, dim=0)
            
            # Extract features
            features = self.extractor.extract_features(batch_tensor)['cls_token']
            
            if normalize:
                features = features / features.norm(dim=-1, keepdim=True)
            
            all_features.append(features)
        
        return torch.cat(all_features, dim=0)
    
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
    
    # Create extractor with DINOv3
    extractor = SurgicalDinoExtractor(use_dinov3=True)
    
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
    print("   extractor = SurgicalDinoExtractor(use_dinov3=True)")
    print("   features = extractor.extract_features(frame_path)")


if __name__ == "__main__":
    demo()
