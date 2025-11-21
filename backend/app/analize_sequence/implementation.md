# Implementation Guide: 二段階フィルタリングシステム

## 概要

`/api/vision/analyze-sequence` エンドポイントに二段階フィルタリング（Stage1: DINOv3視覚的類似度、Stage2: VLM意味的選択）を実装します。

**設計方針**:
- DINOv3はProtocolインターフェース + ダミー実装（後で差し替え）
- S3パス形式を記録（ローカルファイルだが後でS3移行可能）
- 既存エンドポイントを直接修正

---

## 1. ファイル構成

### 作成するファイル

```
backend/app/analize_sequence/
├── __init__.py                  # パッケージ初期化
├── models.py                    # Pydanticモデル
├── protocols.py                 # Stage1Filterインターフェース定義
├── stage1_dummy.py              # DINOv3ダミー実装
├── prompts.py                   # VLMプロンプト
├── stage2_vlm.py                # Stage2 VLMフィルター
└── pipeline.py                  # 統合パイプライン
```

### 修正するファイル

- `/Users/iori/git/surgical-recap/backend/app/main.py` - エンドポイント修正
- `/Users/iori/git/surgical-recap/backend/app/vision.py` - VLM選択メソッド追加

---

## 2. 実装詳細

### 2.1 models.py

**ファイルパス**: `/Users/iori/git/surgical-recap/backend/app/analize_sequence/models.py`

```python
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class FrameMetadata(BaseModel):
    """フレームのメタデータ"""
    frame_number: int
    timestamp: float
    local_path: str
    s3_key: str  # s3://surgical-recap/jobs/{job_id}/frames/...


class Manifest(BaseModel):
    """Stage1出力: DINOv3フィルタリング結果"""
    job_id: str
    video_id: str
    total_frames: int
    keep_indices: List[int]  # Stage1で選択されたフレームのインデックス
    keep_s3_keys: List[str]  # 対応するS3キー
    frames: List[FrameMetadata]


class SelectedFrame(BaseModel):
    """Stage2で選択されたフレーム"""
    global_index: int  # 元の動画でのフレーム番号
    stage1_index: int  # Stage1のkeep_indices内でのインデックス
    local_path: str
    s3_key: str
    batch_id: int
    local_index_in_batch: int  # バッチ内のインデックス (0-4)


class FinalManifest(BaseModel):
    """Stage2出力: VLM意味的フィルタリング結果"""
    job_id: str
    video_id: str
    stage1_frame_count: int
    selected_frame_count: int
    selected_frames: List[SelectedFrame]


class TwoStageFilterRequest(BaseModel):
    """二段階フィルタリングのリクエスト"""
    video_id: str
    max_frames: Optional[int] = None
    window_size: int = Field(default=5, ge=3, le=10)
    overlap: int = Field(default=2, ge=1, le=4)
    job_id: Optional[str] = None  # 指定しない場合は自動生成


class TwoStageFilterResponse(BaseModel):
    """二段階フィルタリングのレスポンス"""
    status: str
    job_id: str
    video_id: str
    manifest: Manifest
    final_manifest: FinalManifest
    analysis_results: Optional[List[Dict]] = None  # 各フレームの解析結果
```

---

### 2.2 protocols.py

**ファイルパス**: `/Users/iori/git/surgical-recap/backend/app/analize_sequence/protocols.py`

```python
from typing import Protocol, List
from .models import Manifest


class Stage1FilterProtocol(Protocol):
    """
    Stage1フィルター（DINOv3）のインターフェース定義

    後でDINOv3実装に差し替え可能
    """

    def filter_frames(
        self,
        video_id: str,
        frame_paths: List[str],
        job_id: str,
        similarity_threshold: float = 0.98,
        sample_interval_sec: int = 10
    ) -> Manifest:
        """
        フレームを視覚的類似度でフィルタリング

        Args:
            video_id: 動画ID
            frame_paths: フレーム画像のローカルパス
            job_id: ジョブID
            similarity_threshold: 類似度閾値 (0.98推奨)
            sample_interval_sec: グループ内サンプリング間隔（秒）

        Returns:
            Manifest: 選択されたフレームのメタデータ
        """
        ...
```

---

### 2.3 stage1_dummy.py

**ファイルパス**: `/Users/iori/git/surgical-recap/backend/app/analize_sequence/stage1_dummy.py`

```python
from typing import List
from pathlib import Path
import weave

from .models import Manifest, FrameMetadata
from .protocols import Stage1FilterProtocol


class DummyStage1Filter:
    """
    DINOv3のダミー実装

    10秒間隔で均等にフレームをサンプリング
    後でDINOv3実装に差し替え
    """

    def __init__(self, fps: float = 1.0):
        """
        Args:
            fps: 動画のフレームレート（cholecSeg8kは1fps想定）
        """
        self.fps = fps

    @weave.op()
    def filter_frames(
        self,
        video_id: str,
        frame_paths: List[str],
        job_id: str,
        similarity_threshold: float = 0.98,
        sample_interval_sec: int = 10
    ) -> Manifest:
        """
        ダミー実装: 10秒間隔でフレームをサンプリング
        """
        # 10秒間隔のフレーム数
        frame_interval = int(sample_interval_sec * self.fps)

        # 均等サンプリング
        keep_indices = list(range(0, len(frame_paths), frame_interval))

        # フレームメタデータ作成
        frames = []
        keep_s3_keys = []

        for idx in keep_indices:
            local_path = frame_paths[idx]
            frame_name = Path(local_path).name

            # S3キー形式（後でアップロード可能）
            s3_key = f"s3://surgical-recap/jobs/{job_id}/frames/{frame_name}"
            keep_s3_keys.append(s3_key)

            frames.append(FrameMetadata(
                frame_number=idx,
                timestamp=idx / self.fps,
                local_path=local_path,
                s3_key=s3_key
            ))

        return Manifest(
            job_id=job_id,
            video_id=video_id,
            total_frames=len(frame_paths),
            keep_indices=keep_indices,
            keep_s3_keys=keep_s3_keys,
            frames=frames
        )


# Protocolチェック（型エラーがないか確認）
def _check_protocol_compliance():
    """型チェック用（実行不要）"""
    dummy: Stage1FilterProtocol = DummyStage1Filter()
    return dummy
```

---

### 2.4 prompts.py

**ファイルパス**: `/Users/iori/git/surgical-recap/backend/app/analize_sequence/prompts.py`

```python
"""
VLM Stage2用プロンプト
"""

SELECTOR_SYSTEM_PROMPT = """You are an expert surgical video analyst specializing in laparoscopic surgery.

Your task is to select the most medically significant keyframes from a sequence of surgical video frames.

Selection criteria:
1. Start/end of surgical actions (e.g., dissection begins, clipping completes)
2. Instrument changes (new tool introduced or removed)
3. Clear anatomical features (critical structures visible)
4. Critical moments (bleeding, completion of critical step, complications)

You will receive 3-5 consecutive frames. Select frames that represent important transitions or moments.

IMPORTANT: Output ONLY valid JSON in this exact format:
{
  "selected_indices": [0, 3],
  "reason": "Frame 0 shows start of clipping, frame 3 shows clip placement completed"
}

The indices must be integers from 0 to N-1 (where N is the number of input frames).
"""


def create_selector_user_prompt(frame_count: int, batch_id: int) -> str:
    """
    ユーザープロンプト生成

    Args:
        frame_count: バッチ内のフレーム数
        batch_id: バッチID（デバッグ用）

    Returns:
        プロンプト文字列
    """
    return f"""Analyze these {frame_count} consecutive frames from a laparoscopic cholecystectomy surgery (Batch #{batch_id}).

Select the frames that are most medically significant based on:
- Surgical action transitions (start/end of cutting, clipping, dissection, etc.)
- Instrument changes
- Clear anatomical structures
- Critical moments

Return JSON with "selected_indices" (list of integers 0-{frame_count-1}) and "reason" (brief explanation).

Example output:
{{
  "selected_indices": [0, 2],
  "reason": "Frame 0 shows dissection start, frame 2 shows clear view of cystic duct"
}}
"""
```

---

### 2.5 stage2_vlm.py

**ファイルパス**: `/Users/iori/git/surgical-recap/backend/app/analize_sequence/stage2_vlm.py`

```python
from typing import List, Dict, Tuple
import weave

from .models import Manifest, FinalManifest, SelectedFrame
from .prompts import SELECTOR_SYSTEM_PROMPT, create_selector_user_prompt


class VLMStage2Filter:
    """
    Stage2: VLM意味的フィルタリング

    Sliding windowでフレームをバッチ処理し、
    医学的に重要なフレームを選択
    """

    def __init__(
        self,
        vision_analyzer,
        window_size: int = 5,
        overlap: int = 2
    ):
        """
        Args:
            vision_analyzer: VisionAnalyzerインスタンス
            window_size: スライディングウィンドウサイズ
            overlap: オーバーラップフレーム数
        """
        self.vision_analyzer = vision_analyzer
        self.window_size = window_size
        self.overlap = overlap
        self.step_size = window_size - overlap

    def _generate_sliding_windows(
        self,
        frames: List,
        window_size: int
    ) -> List[Tuple[int, List]]:
        """
        スライディングウィンドウ生成

        Args:
            frames: フレームのリスト
            window_size: ウィンドウサイズ

        Returns:
            [(batch_id, [frame, ...]), ...]
        """
        windows = []
        batch_id = 0

        for i in range(0, len(frames), self.step_size):
            window = frames[i:i + window_size]
            if len(window) >= 3:  # 最低3フレーム必要
                windows.append((batch_id, window))
                batch_id += 1

        return windows

    def _batch_local_to_global_index(
        self,
        batch_id: int,
        local_index: int
    ) -> int:
        """
        バッチ内のローカルインデックスをグローバルインデックスに変換

        Args:
            batch_id: バッチID
            local_index: バッチ内インデックス (0-4)

        Returns:
            グローバルインデックス (Stage1 keep_indices内)
        """
        return batch_id * self.step_size + local_index

    def _deduplicate_selections(
        self,
        selections: List[Tuple[int, int, int]]
    ) -> List[Tuple[int, int, int]]:
        """
        重複する選択を除去（OR論理）

        Args:
            selections: [(batch_id, local_index, global_index), ...]

        Returns:
            重複除去後のリスト
        """
        # global_indexでユニーク化
        seen = set()
        unique = []

        for batch_id, local_idx, global_idx in selections:
            if global_idx not in seen:
                seen.add(global_idx)
                unique.append((batch_id, local_idx, global_idx))

        return sorted(unique, key=lambda x: x[2])  # global_indexでソート

    @weave.op()
    def filter_frames(
        self,
        manifest: Manifest
    ) -> FinalManifest:
        """
        Stage1の結果から医学的に重要なフレームを選択

        Args:
            manifest: Stage1のManifest

        Returns:
            FinalManifest: 選択されたフレーム
        """
        frames = manifest.frames
        all_selections = []

        # スライディングウィンドウ生成
        windows = self._generate_sliding_windows(frames, self.window_size)

        # 各バッチを処理
        for batch_id, window_frames in windows:
            image_paths = [f.local_path for f in window_frames]

            # VLMで選択
            try:
                selected_indices = self.vision_analyzer.select_keyframes_batch(
                    image_paths=image_paths,
                    batch_id=batch_id
                )

                # グローバルインデックスに変換
                for local_idx in selected_indices:
                    global_idx = self._batch_local_to_global_index(batch_id, local_idx)
                    all_selections.append((batch_id, local_idx, global_idx))

            except Exception as e:
                # エラー時はバッチの中央フレームを選択
                print(f"Warning: Batch {batch_id} failed: {e}. Using center frame.")
                center_idx = len(window_frames) // 2
                global_idx = self._batch_local_to_global_index(batch_id, center_idx)
                all_selections.append((batch_id, center_idx, global_idx))

        # 重複除去
        unique_selections = self._deduplicate_selections(all_selections)

        # SelectedFrame作成
        selected_frames = []
        for batch_id, local_idx, global_idx in unique_selections:
            frame = frames[global_idx]
            selected_frames.append(SelectedFrame(
                global_index=frame.frame_number,
                stage1_index=global_idx,
                local_path=frame.local_path,
                s3_key=frame.s3_key,
                batch_id=batch_id,
                local_index_in_batch=local_idx
            ))

        return FinalManifest(
            job_id=manifest.job_id,
            video_id=manifest.video_id,
            stage1_frame_count=len(frames),
            selected_frame_count=len(selected_frames),
            selected_frames=selected_frames
        )
```

---

### 2.6 pipeline.py

**ファイルパス**: `/Users/iori/git/surgical-recap/backend/app/analize_sequence/pipeline.py`

```python
from typing import List, Optional
import uuid
import weave

from .protocols import Stage1FilterProtocol
from .stage1_dummy import DummyStage1Filter
from .stage2_vlm import VLMStage2Filter
from .models import Manifest, FinalManifest


class TwoStagePipeline:
    """
    二段階フィルタリングパイプライン

    Stage1 (DINOv3) → Stage2 (VLM) を統合
    """

    def __init__(
        self,
        vision_analyzer,
        stage1_filter: Optional[Stage1FilterProtocol] = None,
        window_size: int = 5,
        overlap: int = 2
    ):
        """
        Args:
            vision_analyzer: VisionAnalyzerインスタンス
            stage1_filter: Stage1フィルター（指定しない場合はダミー）
            window_size: Stage2スライディングウィンドウサイズ
            overlap: Stage2オーバーラップ
        """
        self.vision_analyzer = vision_analyzer
        self.stage1_filter = stage1_filter or DummyStage1Filter()
        self.stage2_filter = VLMStage2Filter(
            vision_analyzer=vision_analyzer,
            window_size=window_size,
            overlap=overlap
        )

    @weave.op()
    def process(
        self,
        video_id: str,
        frame_paths: List[str],
        job_id: Optional[str] = None
    ) -> tuple[Manifest, FinalManifest]:
        """
        二段階フィルタリング実行

        Args:
            video_id: 動画ID
            frame_paths: 全フレームのローカルパス
            job_id: ジョブID（指定しない場合は自動生成）

        Returns:
            (manifest, final_manifest)
        """
        if job_id is None:
            job_id = f"job_{uuid.uuid4().hex[:8]}"

        # Stage1: 視覚的類似度フィルタリング
        manifest = self.stage1_filter.filter_frames(
            video_id=video_id,
            frame_paths=frame_paths,
            job_id=job_id
        )

        # Stage2: VLM意味的フィルタリング
        final_manifest = self.stage2_filter.filter_frames(manifest)

        return manifest, final_manifest
```

---

### 2.7 vision.py の修正

**ファイルパス**: `/Users/iori/git/surgical-recap/backend/app/vision.py`

**追加箇所**: `VisionAnalyzer` クラスの最後（line 184以降）

```python
    @weave.op()
    def select_keyframes_batch(
        self,
        image_paths: List[Union[str, Path]],
        batch_id: int = 0
    ) -> List[int]:
        """
        バッチからキーフレームを選択

        Args:
            image_paths: 画像パスのリスト (3-10枚)
            batch_id: バッチID（プロンプト用）

        Returns:
            選択されたインデックスのリスト (0 ~ len(image_paths)-1)
        """
        from .analize_sequence.prompts import (
            SELECTOR_SYSTEM_PROMPT,
            create_selector_user_prompt
        )

        # 画像をbase64エンコード
        image_contents = []
        for img_path in image_paths:
            with open(img_path, "rb") as f:
                import base64
                img_b64 = base64.b64encode(f.read()).decode()
                image_contents.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                })

        # プロンプト構築
        user_prompt = create_selector_user_prompt(
            frame_count=len(image_paths),
            batch_id=batch_id
        )

        messages = [
            {"role": "system", "content": SELECTOR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    *image_contents
                ]
            }
        ]

        # API呼び出し
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=300
        )

        # JSON解析
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            selected_indices = result.get("selected_indices", [])

            # バリデーション
            valid_indices = [
                idx for idx in selected_indices
                if isinstance(idx, int) and 0 <= idx < len(image_paths)
            ]

            if not valid_indices:
                # フォールバック: 中央とエンド
                valid_indices = [0, len(image_paths) // 2]

            return valid_indices

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: JSON parse error in batch {batch_id}: {e}")
            # フォールバック: 最初と中央
            return [0, len(image_paths) // 2]
```

---

### 2.8 main.py の修正

**ファイルパス**: `/Users/iori/git/surgical-recap/backend/app/main.py`

**修正箇所**: `/api/vision/analyze-sequence` エンドポイント（line 171-234を置き換え）

**既存コード（削除）**:
```python
@app.post("/api/vision/analyze-sequence")
def analyze_sequence(request: AnalyzeSequenceRequest):
    """Analyze a sequence of frames"""
    try:
        # ... 既存の実装 ...
```

**新しいコード**:
```python
@app.post("/api/vision/analyze-sequence")
def analyze_sequence(request: AnalyzeSequenceRequest):
    """
    二段階フィルタリングでフレームを解析

    Stage1: DINOv3視覚的類似度（現在はダミー）
    Stage2: VLM意味的選択
    """
    from .analize_sequence.pipeline import TwoStagePipeline
    from .analize_sequence.models import TwoStageFilterResponse
    import uuid

    try:
        # データセット読み込み
        sequence = loader.load_sequence(
            request.video_id,
            load_images=False
        )

        if not sequence:
            raise HTTPException(
                status_code=404,
                detail=f"Video sequence not found: {request.video_id}"
            )

        # max_frames制限
        if request.max_frames:
            sequence = sequence[:request.max_frames]

        # フレームパス抽出
        frame_paths = [frame['image_path'] for frame in sequence]

        # 二段階フィルタリングパイプライン
        pipeline = TwoStagePipeline(
            vision_analyzer=analyzer,
            window_size=5,
            overlap=2
        )

        job_id = f"job_{uuid.uuid4().hex[:8]}"
        manifest, final_manifest = pipeline.process(
            video_id=request.video_id,
            frame_paths=frame_paths,
            job_id=job_id
        )

        # 選択されたフレームのみ解析
        analysis_results = []
        for selected_frame in final_manifest.selected_frames:
            result = analyzer.analyze_frame(
                image_path=selected_frame.local_path,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT
            )
            result['frame_id'] = f"frame_{selected_frame.global_index:06d}"
            result['image_path'] = selected_frame.local_path
            result['s3_key'] = selected_frame.s3_key
            analysis_results.append(result)

        return TwoStageFilterResponse(
            status="ok",
            job_id=job_id,
            video_id=request.video_id,
            manifest=manifest,
            final_manifest=final_manifest,
            analysis_results=analysis_results
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**追加するインポート** (ファイル先頭に追加):
```python
import uuid  # 既存のimportセクションに追加
```

---

## 3. データフロー

```
1. Request (video_id, max_frames)
   ↓
2. CholecSeg8kLoader.load_sequence() → 全フレームパス
   ↓
3. Stage1: DummyStage1Filter (10秒間隔サンプリング)
   → Manifest (keep_indices, keep_s3_keys)
   ↓
4. Stage2: VLMStage2Filter (Sliding window)
   - Window生成 (size=5, overlap=2)
   - VisionAnalyzer.select_keyframes_batch() × N
   - Index mapping & deduplication
   → FinalManifest (selected_frames)
   ↓
5. 選択されたフレームのみ解析
   → VisionAnalyzer.analyze_frame() × selected_count
   ↓
6. Response (manifest, final_manifest, analysis_results)
```

---

## 4. S3パス記録形式

### ローカル開発時

- **実ファイル**: `/Users/iori/git/surgical-recap/backend/data/cholecseg8k/video01/frame_000123.jpg`
- **S3キー記録**: `s3://surgical-recap/jobs/job_a1b2c3d4/frames/frame_000123.jpg`

### 後でS3移行時

1. ローカルファイルをS3にアップロード
2. `s3_key`を使ってファイル取得
3. コード変更不要（パスの切り替えのみ）

---

## 5. DINOv3実装への差し替え手順

### 5.1 新しいフィルターを作成

**ファイル**: `/Users/iori/git/surgical-recap/backend/app/analize_sequence/stage1_dinov3.py`

```python
import torch
from .protocols import Stage1FilterProtocol
from .models import Manifest

class DINOv3Stage1Filter:
    """実際のDINOv3実装"""

    def __init__(self):
        # DINOv3モデル読み込み
        self.model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitb14')
        self.model.eval()

    def filter_frames(self, video_id, frame_paths, job_id, ...) -> Manifest:
        # 実装...
        pass
```

### 5.2 パイプラインで差し替え

**ファイル**: `/Users/iori/git/surgical-recap/backend/app/main.py`

```python
# 修正前
pipeline = TwoStagePipeline(
    vision_analyzer=analyzer,
    # stage1_filter=None (デフォルトでダミー)
)

# 修正後
from .analize_sequence.stage1_dinov3 import DINOv3Stage1Filter

pipeline = TwoStagePipeline(
    vision_analyzer=analyzer,
    stage1_filter=DINOv3Stage1Filter()  # ← ここだけ変更
)
```

**Protocolのおかげで、インターフェースが一致していれば差し替え完了！**

---

## 6. テスト方法

### 6.1 ローカルテスト

```bash
# Backend起動
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

### 6.2 APIリクエスト

```bash
curl -X POST "http://localhost:8000/api/vision/analyze-sequence" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "video01",
    "max_frames": 30
  }'
```

### 6.3 期待されるレスポンス

```json
{
  "status": "ok",
  "job_id": "job_a1b2c3d4",
  "video_id": "video01",
  "manifest": {
    "job_id": "job_a1b2c3d4",
    "video_id": "video01",
    "total_frames": 30,
    "keep_indices": [0, 10, 20],
    "keep_s3_keys": ["s3://...", "s3://...", "s3://..."],
    "frames": [...]
  },
  "final_manifest": {
    "job_id": "job_a1b2c3d4",
    "video_id": "video01",
    "stage1_frame_count": 3,
    "selected_frame_count": 2,
    "selected_frames": [...]
  },
  "analysis_results": [
    {
      "step": "Dissection",
      "instruments": ["Hook", "Grasper"],
      "risk": "Medium",
      "description": "胆嚢の剥離",
      "frame_id": "frame_000000",
      "s3_key": "s3://surgical-recap/jobs/..."
    },
    ...
  ]
}
```

---

## 7. W&B Weaveでのトレーシング

すべての重要な関数に `@weave.op()` デコレータを付与済み:

- `DummyStage1Filter.filter_frames()`
- `VLMStage2Filter.filter_frames()`
- `TwoStagePipeline.process()`
- `VisionAnalyzer.select_keyframes_batch()`
- `VisionAnalyzer.analyze_frame()`

### Weave UIで確認できる情報

- 各Stage の入力/出力
- 選択されたフレーム数の推移
- VLMの選択理由（プロンプト/レスポンス）
- レイテンシとコスト

---

## 8. ハッカソン用の簡略化ポイント

### ✅ 実装済み

- Stage1はダミー（10秒間隔サンプリング）
- Stage2は完全実装（VLM sliding window）
- S3パス形式を記録（実際のアップロードは後回し）
- エラーハンドリング（フォールバック: 中央フレーム選択）

### ⚠️ 後回し

- 並列バッチ処理（現在は逐次）
- manifest.json / final_manifest.json のファイル保存
- S3への実際のアップロード
- ジョブステータス管理

---

## 9. トラブルシューティング

### 問題: JSON解析エラー

**原因**: VLMが不正なJSONを返す

**対策**: フォールバックロジック実装済み（中央フレーム選択）

### 問題: メモリ不足

**原因**: 大量の画像をbase64エンコード

**対策**:
- `max_frames` を制限（30-50フレーム推奨）
- バッチサイズ削減（window_size=3）

### 問題: Stage1が遅い

**原因**: ダミー実装でも全フレーム読み込み

**対策**:
- `CholecSeg8kLoader` で `load_images=False` を使用
- パスのみ渡す

---

## 10. 実装チェックリスト

- [ ] `analize_sequence/__init__.py` 作成
- [ ] `analize_sequence/models.py` 作成
- [ ] `analize_sequence/protocols.py` 作成
- [ ] `analize_sequence/stage1_dummy.py` 作成
- [ ] `analize_sequence/prompts.py` 作成
- [ ] `analize_sequence/stage2_vlm.py` 作成
- [ ] `analize_sequence/pipeline.py` 作成
- [ ] `vision.py` に `select_keyframes_batch()` 追加
- [ ] `main.py` のエンドポイント修正
- [ ] ローカルでテスト（30フレーム）
- [ ] W&B Weaveでトレース確認

---

## まとめ

この実装により、以下が実現されます:

1. **二段階フィルタリング**: DINOv3（ダミー）+ VLM（完全実装）
2. **Protocol設計**: DINOv3を後で差し替え可能
3. **S3準備**: パス形式を記録し、後でアップロード可能
4. **ハッカソン対応**: 最小限の実装で動作確認可能
5. **拡張性**: 並列化、ジョブ管理などを後で追加可能

**推定実装時間**: 3-4時間
