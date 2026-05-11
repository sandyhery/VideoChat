"""
OCR 服务 - 支持 RapidOCR、PaddleOCR、Tesseract
优先使用 RapidOCR（更快更准确），回退到 Tesseract
"""
import os
import cv2
import numpy as np
from typing import List, Dict, Optional


def get_paddle_ocr(lang: str = 'ch'):
    """
    获取 PaddleOCR 实例

    Args:
        lang: 语言，'ch' 表示中文，'en' 表示英文
    """
    from paddleocr import PaddleOCR

    return PaddleOCR(lang=lang, use_doc_orientation_classify=False, use_doc_unwarping=False)


def ocr_image(image_path: str, lang: str = 'ch', region: str = 'subtitle') -> Dict:
    """
    使用 RapidOCR 识别图像中的文字
    如果 RapidOCR 不可用，回退到 Tesseract OCR

    Args:
        image_path: 图像路径
        lang: 语言
        region: 识别区域，'subtitle' 表示只识别字幕区域（底部20%），'full' 表示全图识别
    """
    import cv2

    # 如果是字幕区域，先裁剪
    if region == 'subtitle':
        try:
            image = cv2.imread(image_path)
            if image is not None:
                height, width = image.shape[:2]
                # 截取底部字幕区域 (80%-98%)
                y_start = int(height * 0.80)
                y_end = int(height * 0.98)
                subtitle_crop = image[y_start:y_end, :]
                # 保存裁剪后的临时文件
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                cv2.imwrite(temp_file.name, subtitle_crop)
                image_path = temp_file.name
        except Exception as e:
            print(f"[OCR] 裁剪字幕区域失败: {e}")

    # 优先使用 RapidOCR
    try:
        from rapidocr import RapidOCR

        ocr = RapidOCR()
        result = ocr(image_path)

        if not result or not hasattr(result, 'txts') or not result.txts:
            return {
                "text": "",
                "boxes": [],
                "confidence": 0.0,
                "lines": []
            }

        # 解析 RapidOCR 结果
        lines = list(result.txts) if result.txts else []
        boxes = result.boxes.tolist() if result.boxes is not None and len(result.boxes) > 0 else []
        scores = result.scores if result.scores else []
        confidences = [float(s) for s in scores]

        full_text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "text": full_text,
            "boxes": boxes,
            "confidence": avg_confidence,
            "lines": lines,
            "method": "rapidocr"
        }
    except ImportError:
        pass
    except Exception as e:
        print(f"[RapidOCR] Error: {e}")

    # 回退到 Tesseract OCR
    try:
        import pytesseract
        import cv2
        import numpy as np
        from PIL import Image

        pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'

        image = cv2.imread(image_path)
        if image is None:
            return {"text": "", "boxes": [], "confidence": 0.0, "lines": [], "error": "Cannot read image"}

        height, width = image.shape[:2]

        # 截取底部字幕区域 (82%-98%)
        y_start = int(height * 0.82)
        y_end = int(height * 0.98)
        crop = image[y_start:y_end, :]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # CLAHE 增强对比度
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 放大 2 倍
        scale = 2
        big = cv2.resize(enhanced, (width * scale, enhanced.shape[0] * scale), interpolation=cv2.INTER_CUBIC)

        # OTSU 二值化 + 反转（字幕通常是亮底深色字）
        _, binary = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        inverted = cv2.bitwise_not(binary)

        # 形态学处理
        kernel = np.ones((1, 2), np.uint8)
        cleaned = cv2.morphologyEx(inverted, cv2.MORPH_CLOSE, kernel)

        pil_img = Image.fromarray(cleaned)

        # 使用 PSM 3（完整页面或单列）
        text = pytesseract.image_to_string(pil_img, lang='chi_sim+eng', config='--oem 3 --psm 3')
        text = text.strip()

        # 获取置信度
        data = pytesseract.image_to_data(pil_img, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)
        confidences = [float(c) for c in data['conf'] if float(c) > 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0

        lines = [l.strip() for l in text.split('\n') if l.strip()]

        return {
            "text": text,
            "boxes": [],
            "confidence": avg_conf / 100.0,
            "lines": lines,
            "method": "tesseract"
        }
    except Exception as tesseract_error:
        print(f"[Tesseract] OCR failed: {tesseract_error}")
        return {
            "text": "",
            "boxes": [],
            "confidence": 0.0,
            "lines": [],
            "error": str(tesseract_error)
        }


def ocr_images(image_paths: List[str], lang: str = 'ch', region: str = 'subtitle') -> List[Dict]:
    """
    批量识别多个图像

    Args:
        image_paths: 图像文件路径列表
        lang: 语言
        region: 识别区域，'subtitle' 表示只识别字幕区域（底部20%），'full' 表示全图识别

    Returns:
        结果列表
    """
    results = []
    for image_path in image_paths:
        result = ocr_image(image_path, lang, region)
        result["image_path"] = image_path
        results.append(result)
    return results


def detect_subtitle_with_paddle(image_path: str, region: str = 'bottom') -> Dict:
    """
    使用 PaddleOCR 检测字幕 - 优化版

    Args:
        image_path: 图像文件路径
        region: 字幕区域 'bottom' 或 'full'

    Returns:
        包含字幕信息的字典
    """
    import cv2
    import numpy as np

    try:
        image = cv2.imread(image_path)
        if image is None:
            return {"text": "", "confidence": 0.0, "lines": []}

        height, width = image.shape[:2]

        # 根据区域裁剪图像
        if region == 'bottom':
            # 使用自适应检测 + 回退固定区域的策略
            y_start, y_end = _find_subtitle_region(image)

            # 如果自适应检测失败（返回全图），使用固定底部区域
            if y_end - y_start < height * 0.05:
                y_start = int(height * 0.80)
                y_end = int(height * 0.98)

            crop = image[y_start:y_end, :]
        elif region == 'lower_third':
            y_start = int(height * 0.66)
            crop = image[y_start:, :]
        else:
            crop = image
            y_start = 0
            y_end = height

        # 保存裁剪后的图像用于 OCR
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            cv2.imwrite(f.name, crop)
            temp_path = f.name

        # OCR 识别
        result = ocr_image(temp_path, lang='ch')
        os.unlink(temp_path)

        # 过滤非字幕内容（标题等不在底部的文字）
        if result.get("lines"):
            filtered_lines = _filter_subtitle_lines(result["lines"], result.get("boxes", []), y_start, height)
            result["lines"] = filtered_lines
            result["text"] = "\n".join(filtered_lines)

        if result.get("lines"):
            result["region"] = f"bottom_{y_start}_{y_end}"
        else:
            result["region"] = "full"

        return result

    except Exception as e:
        print(f"PaddleOCR subtitle detection error: {e}")
        return {"text": "", "confidence": 0.0, "lines": [], "error": str(e)}


def _find_subtitle_region(image: np.ndarray) -> tuple:
    """
    智能检测字幕区域 - 通过分析底部亮度分布找到字幕条

    Returns:
        (y_start, y_end) - 字幕区域的起止 Y 坐标
    """
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 分析底部 75-100% 区域的亮度分布
    bottom_start = int(height * 0.75)
    bottom_region = gray[bottom_start:, :]

    # 找每一行的平均亮度
    row_means = np.mean(bottom_region, axis=1)

    # 计算基线（不包含最亮部分的平均）
    sorted_means = sorted(row_means)
    baseline = np.mean(sorted_means[:len(sorted_means)//2])

    # 字幕条比背景亮 20 以上
    threshold = baseline + 20

    subtitle_rows = []
    for i, mean in enumerate(row_means):
        if mean > threshold:
            subtitle_rows.append(i)

    if not subtitle_rows or len(subtitle_rows) < 5:
        # 返回全图表示未检测到
        return (0, height)

    # 找到连续的高亮度区域（字幕条）
    y_start = subtitle_rows[0] + bottom_start
    y_end = subtitle_rows[-1] + bottom_start

    # 扩展边距
    margin = max(10, (y_end - y_start) // 3)
    y_start = max(bottom_start, y_start - margin)
    y_end = min(height, y_end + margin)

    return y_start, y_end


def _filter_subtitle_lines(lines: List[str], boxes: List, region_start: int, image_height: int) -> List[str]:
    """
    过滤非字幕内容 - 字幕通常在图像底部，文字较短

    Args:
        lines: 识别出的文本行
        boxes: 对应的边界框
        region_start: 裁剪区域起始 Y
        image_height: 图像总高度

    Returns:
        过滤后的文本行
    """
    if not lines:
        return []

    filtered = []
    for i, line in enumerate(lines):
        text = line.strip()
        if not text or len(text) < 2:
            continue

        # 字幕通常是较短的文本（10个字以内）
        # 如果文本太长，可能是标题或其他内容
        if len(text) > 20:
            continue

        # 保留中文、字母、数字
        import re
        meaningful_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbfa-zA-Z0-9]', text)
        if len(meaningful_chars) / max(len(text), 1) < 0.3:
            continue

        filtered.append(text)

    return filtered


def filter_paddle_ocr_results(ocr_results: List[Dict], min_length: int = 2,
                             min_confidence: float = 0.5) -> List[Dict]:
    """
    过滤有意义的 OCR 结果

    Args:
        ocr_results: OCR 结果列表
        min_length: 最小文本长度
        min_confidence: 最小置信度

    Returns:
        过滤后的结果
    """
    import re

    filtered = []
    for result in ocr_results:
        text = result.get('text', '').strip()
        confidence = result.get('confidence', 0)

        # 基本过滤
        if len(text) < min_length:
            continue
        if confidence < min_confidence:
            continue

        # 检查是否有意义的字符
        meaningful = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf a-zA-Z0-9]', text)
        if len(meaningful) / max(len(text), 1) < 0.3:
            continue

        filtered.append(result)

    return filtered


# 导出函数
def extract_text_from_image(image_path: str, lang: str = 'ch') -> Dict:
    """从图像中提取文字"""
    return ocr_image(image_path, lang)


def extract_text_from_images(image_paths: List[str], lang: str = 'ch', region: str = 'subtitle') -> List[Dict]:
    """批量从多个图像中提取文字"""
    return ocr_images(image_paths, lang, region)


def detect_subtitles(image_path: str, lang: str = 'ch') -> Dict:
    """检测图像中的字幕"""
    return detect_subtitle_with_paddle(image_path, region='bottom')


def normalize_chinese_text(text: str, target: str = 'simplified') -> str:
    """规范化中文文本"""
    if not text:
        return text

    try:
        import opencc
        converter = opencc.OpenCC('t2s' if target == 'simplified' else 's2t')
        return converter.convert(text)
    except ImportError:
        return _simple_chinese_convert(text, target)
    except Exception:
        return text


def _simple_chinese_convert(text: str, target: str = 'simplified') -> str:
    """简繁转换"""
    t2s = {
        '電': '电', '網': '网', '時': '时', '會': '会', '資': '资',
        '業': '业', '開': '开', '發': '发', '關': '关', '員': '员',
        '題': '题', '義': '义', '學': '学', '動': '动', '機': '机',
        '場': '场', '產': '产', '經': '经', '統': '统', '計': '计',
        '們': '们', '對': '对', '於': '于', '國': '国', '際': '际',
    }
    s2t = {v: k for k, v in t2s.items()}
    result = []
    for char in text:
        result.append(t2s.get(char, char) if target == 'simplified' else s2t.get(char, char))
    return ''.join(result)