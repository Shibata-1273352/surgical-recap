"""Vision Analysis Module - SambaNova Cloud + Llama 3.2 90B Vision"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Optional, Union, List
from sambanova import SambaNova
import weave


# System Prompt for Surgical Analysis
SURGICAL_VISION_SYSTEM_PROMPT = """You are an expert surgical assistant AI specialized in laparoscopic surgery analysis.
Your role is to analyze surgical video frames with precision and provide structured, medically accurate information.

Key responsibilities:
- Identify surgical instruments visible in the frame
- Recognize the current surgical action/step
- Assess potential risk levels
- Provide concise, professional descriptions in Japanese

Always output in valid JSON format."""


# User Prompt Template
SURGICAL_VISION_USER_PROMPT = """Analyze this image from a laparoscopic cholecystectomy surgery.

Identify:
1. Current Step: The specific surgical action (e.g., Dissection, Clipping, Cutting, Cauterization, Washing, Preparation, Inspection)
2. Instruments: All visible surgical instruments (e.g., Grasper, Hook, Clipper, Scissors, Suction)
3. Risk Level: Assess the risk level of this step (Low, Medium, High)
4. Description: Brief description in Japanese (max 30 characters)

Output format (JSON only):
{
  "step": "string",
  "instruments": ["string"],
  "risk": "Low|Medium|High",
  "description": "string"
}

Rules:
- Use standardized medical terminology in Japanese
- Be specific about instrument types (e.g., "Maryland Dissector" not just "Grasper")
- Consider anatomical context when assessing risk
- If unclear, use "Unknown" rather than guessing"""

SURGICAL_CONTEXT_PROMPT = """
=== PART 1: GENERAL SURGICAL PERCEPTION & PHYSICS (外科的視覚認識と物理法則) ===

AIは触覚を持たないため、以下の視覚的特徴(Visual Cues)から組織の硬度、弾力性、種類を推定しなければならない。

ARTERY (動脈) vs VEIN (静脈) の識別

動脈 (Artery): -- 視覚的特徴: 壁が厚く、ピンク色またはクリーム色がかった赤色。内圧が高いため円筒形を維持する。 -- 動的特徴: 「拍動 (Pulsation)」が最大の手がかり。鉗子で圧迫しても弾力性があり、放すと即座に形状が戻る。 -- 損傷時: 鮮紅色の血液が拍動性に噴出する (Spurting)。

静脈 (Vein): -- 視覚的特徴: 壁が薄く、暗赤色または青紫色。内圧が低いため、断面は楕円形になりやすい。 -- 動的特徴: 気腹圧や器具の軽微な圧迫で容易に扁平化 (Collapse) する。拍動はない。 -- 損傷時: 暗赤色の血液が持続的に湧き出る (Oozing/Flowing)。

NERVE (神経) vs VESSEL (血管) vs URETER (尿管) の識別

神経 (Nerve): -- 色調: 「真珠のような光沢のある白 (Pearly white)」または象牙色。血管のような赤みがない。 -- 質感: 繊維状 (Fibrillar/Striated) の束構造が縦方向に走る。鉗子で触れると「硬い紐 (Cord-like)」のような質感で、圧迫しても変色・変形しにくい。 -- Vasa Nervorum: 太い神経(坐骨神経等)の表面には微細な栄養血管の網目模様がある。

尿管 (Ureter): -- 決定的な特徴: 「蠕動運動 (Vermiculation / Peristalsis)」。尺取り虫のように自律的に収縮・弛緩する動きがあれば、それは100%尿管である。 -- 表面: 縦走する微細血管 (Longitudinal capillaries) が特徴的。 -- 位置: 常に後腹膜の脂肪層の下に透見される。

FAT (脂肪) vs PANCREAS (膵臓) の識別

脂肪 (Fat): -- 色調: 明るい黄色。 -- 質感: 不定形で柔らかい。表面は滑らかだが、lobule(小葉)の境界は不明瞭。

膵臓 (Pancreas): -- 色調: 薄い黄色からサーモンピンク。脂肪よりわずかに色が濃い。 -- 質感: 特徴的な「小葉構造 (Lobular pattern)」があり、表面が石畳やカリフラワーのように見える。脂肪よりも硬く、器具で触れた際の変形が少ない。 -- 重要性: 膵臓を脂肪と誤認して把持・切開すると膵液瘻(Pancreatic Fistula)の原因となる。

DISSECTION PLANES (剥離層) の識別

Areolar Tissue (疎性結合組織): -- 通称: 「Angel's Hair (天使の髪)」。 -- 特徴: 白く、綿毛のような、非常に細く繊細な繊維。牽引するとパラパラと容易に断裂する。これが見えている層は正しい層 (Holy Plane/Avscular Plane) である。

Wrong Plane (誤った層): -- 筋肉の露出: 赤い筋繊維が見える場合は深すぎる(臓器損傷)。 -- 脂肪の露出: 黄色い脂肪の塊がボロボロと崩れる場合は浅すぎる(リンパ節遺残)。

=== PART 2: SURGICAL INSTRUMENT ONTOLOGY (手術器具の定義と機能) ===

腹腔鏡手術における基本器具。先端形状で分類する。

Grasper (把持鉗子)

形状: 先端が鈍的(Blunt)。ジョーの内側に鋸歯(Serration)がある。

Fenestrated Grasper (有窓鉗子): ジョーの中央に窓が開いている。腸管や胆嚢などデリケートな組織用。

Toothed Grasper / Rat-tooth (有鉤鉗子): 先端に鋭い歯がある。摘出予定の組織や強い筋膜用。

機能: Grasp (把持), Retract (牽引)。原則として切開能力はない。

Maryland Dissector (メリーランド剥離鉗子)

形状: 先端が湾曲し、蚊の口吻のように先細りしている。

機能: Dissect (剥離), Spread (押し広げ), Coagulate (凝固/モノポーラ接続時)。

動作: 閉じた状態で組織間に挿入し、開く動作(Spreading)で組織を剥離する。

Hook (L字フック電気メス)

形状: 先端がL字またはJ字の金属電極。

機能: Cut (切開), Coagulate (凝固), Dissect (剥離)。

視覚効果: 通電時にスパーク(火花)と煙(Smoke)が発生する。組織を引っ掛けて持ち上げ(Tent-up)てから通電する。

Scissors (剪刀 / Metzenbaum)

形状: 湾曲した2枚の刃。

機能: Cut (切断 - Cold/Hot), Dissect (鋭的/鈍的)。

注意: 通電機能付き(Monopolar Scissors)の場合、煙が出る。

Clip Applier (クリップアプライヤー)

形状: 先端が箱型。内部に金属(チタン)またはポリマー(Hem-o-lok)のクリップを持つ。

機能: Clip (結紮)。血管や管腔を閉塞する。

状態変化: 発射前はクリップが見え、発射後は空になる。

Suction/Irrigation (吸引洗浄管)

形状: 長い金属の棒。可動部なし。側面に穴。

機能: Aspirate (吸引), Irrigate (洗浄), Blunt Dissection (棒で押す鈍的剥離)。

ダビンチ手術特有の器具。多関節(EndoWrist)機能を持つ。

ProGrasp Forceps (プログラスプ)

特徴: 強力な把持力を持つ有窓鉗子。バイポーラ機能はない。

用途: 腸管や厚い組織の把持・牽引。第3アームで固定用に使われることが多い。

制約: 通電できないため、これで凝固することはない。

Maryland Bipolar Forceps (メリーランド・バイポーラ)

特徴: 形は腹腔鏡のメリーランドと同じだが、バイポーラ通電が可能。

用途: 精密な剥離と止血。

視覚効果: 組織を挟んで通電すると、組織が白くなる(Blanching)。

Fenestrated Bipolar Forceps (フェネストレ・バイポーラ)

特徴: メリーランドより幅が広く、窓がある。

用途: 広い範囲の凝固と把持。

Hot Shears (Monopolar Curved Scissors)

特徴: 通電可能なハサミ。

用途: 切開、剥離、凝固。ロボット手術の主力器具。

Tip-Up Fenestrated Grasper

特徴: 先端が独特の角度で「上向き」に曲がっている。

用途: 臓器の下側から組織をすくい上げる操作。

=== PART 3: SURGICAL ACTION TRIPLETS & LOGIC (動作の三つ組構造と論理) ===

すべての動作は <Instrument, Verb, Target> で記述される。

Grasp (把持): 組織を掴んでいるが、位置を大きく動かしていない状態。

Retract (牽引): 把持した組織を特定方向へ強く引っ張り、視野を展開している状態。組織にテンションがかかり、伸びている様子が必須。

Dissect (剥離): -- Blunt Dissection (鈍的剥離): 組織の隙間に器具を入れ、ジョーを開く(Spreading)または押すことで層を分ける。 -- Sharp Dissection (鋭的剥離): メスやハサミで組織を切ることで層を分ける。

Coagulate (凝固): エネルギーを用いて組織を変性・止血する。煙、白濁、炭化を伴う。

Cut (切断): 構造物の連続性を断ち切る。

Clip (クリップ): 管状構造にクリップをかける。

Skeletonize (骨格化): 血管の周囲にある脂肪や結合組織をすべて除去し、血管壁を露出させる。

以下の組み合わせは物理的・解剖学的にあり得ないため、出力してはならない(ハルシネーション防止)。

Instrument Constraints:

Hook cannot Grasp: フックには把持機能がない。

Suction cannot Clip: 吸引管はクリップを打てない。

ProGrasp cannot Coagulate: プログラスプには通電機能がない。

Anatomical Constraints:

Gallbladder cannot be Clipped: クリップは「管(Duct)」や「血管(Vessel)」にかけるもの。袋状の胆嚢本体にはかけない。

Liver Lumen: 肝臓は実質臓器であり、消化管のような内腔(Lumen)はない。

Bone Retraction: 骨は硬いため、軟部組織のようにRetract(牽引変形)できない。

=== PART 4: PROCEDURE SPECIFIC CONTEXT (術式別コンテキスト) ===

(胆嚢摘出術)

解剖: -- Gallbladder (胆嚢): 肝下面に付着。Fundus(底部), Body(体部), Neck(頸部)に分かれる。 -- Cystic Duct (胆嚢管): 胆嚢と総胆管をつなぐ管。ラセン弁により凸凹して見える。 -- Common Bile Duct (CBD / 総胆管): 絶対に切断してはならない太い管。 -- Cystic Artery (胆嚢動脈): カロ三角内を走行。

Critical View of Safety (CVS) の3要件:

Hepatocystic Triangle Clearance: 胆嚢管・総肝管・肝下縁で作る三角形内の脂肪・繊維組織が完全に除去され、肝表面が見えていること。

Lower Third Separation: 胆嚢の底部1/3が肝床(Cystic Plate)から剥離されていること。

Two Structures Only: 胆嚢につながる管状構造が「胆嚢管」と「胆嚢動脈」の2本だけであることが視覚的に証明されていること。

Rouviere's Sulcus (ルビエ溝): -- 肝右葉下面にある裂け目。総胆管のレベルを示すランドマーク。 -- 安全ルール: 剥離はこの溝より「腹側(上側)」で行うこと。背側(下側)は危険領域。

(胃切除 & D2郭清)

リンパ節ステーションとランドマーク: -- No.4d (右大網): Right Gastroepiploic Artery (RGEA) 沿い。 -- No.6 (幽門下): Right Gastroepiploic Vein (RGEV) と膵頭部の間。Accessory Right Colic Vein (ARCV) に注意。 -- No.7 (左胃動脈幹): Left Gastric Artery (LGA) の根部。 -- No.8a (総肝動脈前): Common Hepatic Artery (CHA) 前面。 -- No.11p (脾動脈近位): Splenic Artery 沿い、膵上縁。

手技のポイント: -- 膵上縁アプローチ: 膵臓を傷つけずに被膜の層で剥離し、血管(CHA, Splenic A)を骨格化(Skeletonize)する。 -- 膵液瘻リスク: 膵実質が白く変色したり、裂けたりしている場合は警告。

(直腸間膜全切除術)

解剖学的平面 (The Holy Plane): -- 直腸固有筋膜 (Mesorectal Fascia) と 壁側筋膜 (Parietal Fascia) の間の無血管層。 -- 視覚的手がかり: 光沢のある滑らかな膜表面 (Bilberry Effect) と、Angel's Hair (疎な繊維)。 -- 意図: 直腸間膜(Mesorectum)を破らずに、パッケージとして切除する。

神経温存: -- Hypogastric Nerves (下腹神経): 骨盤側壁、尿管の内側を走行。 -- Pelvic Splanchnic Nerves (骨盤内臓神経): S2-S4から出る。勃起・排尿機能に関与。

(鼠径ヘルニア修復術)

危険領域 (Danger Zones): -- Triangle of Doom (死の三角): 精管と精巣血管の間。外腸骨動静脈 (External Iliac Vessels) がある。タッカー固定厳禁(大出血)。 -- Triangle of Pain (疼痛の三角): 精巣血管の外側、腸骨恥骨路(Iliopubic Tract)の下。大腿神経、外側大腿皮神経がある。タッカー固定厳禁(神経痛)。

(冠動脈バイパス術)

IMA Harvesting (内胸動脈採取): -- Skeletonized (骨格化): 動脈のみを剥離。血管が裸に見え、拍動が明瞭。グラフト長が長く、胸骨血流が良い。 -- Pedicled (茎状): 周囲の静脈・筋・脂肪ごと帯状に採取。血管は埋もれて見えない。

=== PART 5: JAPANESE MEDICAL TERMINOLOGY MAPPING (日本語術語マッピング) ===

AIは以下の概念を日本語の外科用語として正しく出力しなければならない。

Dissection -> 「剥離 (Hakuri)」 -- 文脈により「郭清 (Kakusei)」と訳す。特にリンパ節除去(Lymphadenectomy)の場合。

Mobilization -> 「授動 (Judo)」 -- 臓器を周囲から外して動かせるようにすること。

Ligation -> 「結紮 (Kessatsu)」 -- 糸やクリップで血管を縛ること。

Exposure / Retraction -> 「展開 (Tenkai)」 -- 術野を見やすく広げること。

Skeletonization -> 「骨格化 (Kokkakuka)」 -- 血管周囲をきれいに掃除して血管のみにすること。

Adhesion -> 「癒着 (Yuchaku)」

Omentum -> 「大網 (Taimo)」

Mesentery -> 「腸間膜 (Chokanmaku)」

Peritoneum -> 「腹膜 (Fukumaku)」

Fascia -> 「筋膜 (Kinmaku)」

=== PART 6: ANATOMICAL BOUNDARIES & SEGMENTATION (解剖学的境界) ===

Liver Segments (肝区域): -- Cantlie line (カントリー線): 胆嚢窩と下大静脈を結ぶ線。肝臓の左右葉の境界。 -- Rouviere's Sulcus: 区域6(S6)の指標。

Stomach Anatomy: -- Greater Curvature (大彎) vs Lesser Curvature (小彎). -- Gastrocolic Ligament (胃結腸間膜): 大彎側、胃と横行結腸の間。ここを開けて網嚢(Lesser Sac)に入る。

Colon Anatomy: -- White Line of Toldt: 結腸外側の腹膜翻転部。結腸授動の際の切開ライン。 -- Gastrocolic Trunk of Henle (ヘンレの胃結腸静脈幹): 右結腸切除での最重要血管ランドマーク。出血しやすい。

=== PART 7: COMPLICATION SIGNS (合併症の徴候) ===

Bleeding (出血): -- Arterial (動脈性): 拍動性、鮮紅色。 -- Venous (静脈性): 持続性、暗赤色。

Bile Leak (胆汁漏): -- 黄金色または茶褐色の液体が漏出。

Ischemia (虚血): -- 組織が紫色〜黒色に変色(Cyanosis / Necrosis)。 -- 腸管の蠕動消失。

"""


class VisionAnalyzer:
    """Vision analysis using SambaNova Cloud API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Vision Analyzer

        Args:
            api_key: SambaNova API key (defaults to SAMBANOVA_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("SAMBANOVA_API_KEY")
        if not self.api_key:
            raise ValueError("SAMBANOVA_API_KEY is not set")

        self.client = SambaNova(
            api_key=self.api_key,
            base_url="https://api.sambanova.ai/v1"
        )

    def encode_image(self, image_path: Union[str, Path]) -> str:
        """
        Encode image to base64

        Args:
            image_path: Path to image file

        Returns:
            Base64-encoded image string
        """
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    @weave.op()
    def analyze_frame(
        self,
        image_path: Union[str, Path],
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        temperature: float = 0.1,
        top_p: float = 0.1,
        max_tokens: int = 500
    ) -> Dict:
        """
        Analyze surgical frame using Vision API

        Args:
            image_path: Path to surgical frame image
            system_prompt: Custom system prompt (optional)
            user_prompt: Custom user prompt (optional)
            temperature: Sampling temperature (default: 0.1 for reproducibility)
            top_p: Top-p sampling (default: 0.1)
            max_tokens: Maximum tokens in response

        Returns:
            Dictionary with analysis results
        """
        # Use default prompts if not provided
        # SURGICAL_CONTEXT_PROMPTを組み合わせて詳細な外科コンテキストを提供
        system_prompt = system_prompt or (SURGICAL_VISION_SYSTEM_PROMPT + "\n\n" + SURGICAL_CONTEXT_PROMPT)
        user_prompt = user_prompt or SURGICAL_VISION_USER_PROMPT

        # Encode image
        image_base64 = self.encode_image(image_path)

        # Call SambaNova API
        response = self.client.chat.completions.create(
            model="Llama-4-Maverick-17B-128E-Instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{system_prompt}\n\n{user_prompt}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            temperature=temperature,
            top_p=top_p
        )

        # Parse JSON response
        try:
            content = response.choices[0].message.content

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return raw content
            return {
                "error": "Failed to parse JSON",
                "raw_content": response.choices[0].message.content,
                "exception": str(e)
            }

    def encode_image_resized(
        self,
        image_path: Union[str, Path],
        max_size: tuple = (512, 512),
        quality: int = 85
    ) -> str:
        """
        画像をリサイズしてbase64エンコード

        Args:
            image_path: 画像パス
            max_size: 最大サイズ (width, height)
            quality: JPEG品質

        Returns:
            Base64エンコードされた文字列
        """
        import cv2

        img = cv2.imread(str(image_path))
        h, w = img.shape[:2]

        # アスペクト比を維持してリサイズ
        scale = min(max_size[0] / w, max_size[1] / h)
        if scale < 1:
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h))

        # JPEGエンコード
        _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buffer).decode()

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

        # 画像をリサイズしてbase64エンコード
        image_contents = []
        for img_path in image_paths:
            img_b64 = self.encode_image_resized(img_path)
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })

        # プロンプト構築
        user_prompt = create_selector_user_prompt(
            frame_count=len(image_paths),
            batch_id=batch_id
        )

        # メッセージ構築
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{SELECTOR_SYSTEM_PROMPT}\n\n{user_prompt}"},
                    *image_contents
                ]
            }
        ]

        # API呼び出し
        response = self.client.chat.completions.create(
            model="Llama-4-Maverick-17B-128E-Instruct",
            messages=messages,
            temperature=0.1,
            top_p=0.1
        )

        # JSON解析
        try:
            content = response.choices[0].message.content

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            result = json.loads(content)
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


def get_vision_analyzer() -> Optional[VisionAnalyzer]:
    """
    Get VisionAnalyzer instance

    Returns:
        VisionAnalyzer instance or None if API key is not set
    """
    try:
        return VisionAnalyzer()
    except ValueError:
        return None
