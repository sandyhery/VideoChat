import os
import cv2
from PIL import Image
import numpy as np
from typing import List, Dict, Tuple, Optional
import tempfile

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("警告: pytesseract未安装，OCR功能将被禁用")


class OCRService:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'

    def detect_subtitle_from_frame(self, image_path: str, lang: str = 'chi_sim+eng') -> Dict:
        """
        优化的字幕检测 - 针对视频字幕
        """
        if not TESSERACT_AVAILABLE:
            return {"text": "", "confidence": 0.0, "method": "none"}

        try:
            image = cv2.imread(image_path)
            if image is None:
                return {"text": "", "confidence": 0.0, "method": "none"}

            height, width = image.shape[:2]
            best_text = ""
            best_conf = 0.0
            best_method = ""

            # 方法1: 检测并使用最佳字幕区域
            subtitle_regions = self._find_subtitle_regions(image)
            for region_info in subtitle_regions:
                y_start, y_end = region_info['y_start'], region_info['y_end']
                region = image[y_start:y_end, :]

                if region.size == 0:
                    continue

                # 尝试多种 OCR 配置
                result = self._ocr_region_with_configs(region, lang)
                if result['confidence'] > best_conf and len(result['text'].strip()) > len(best_text.strip()) * 0.8:
                    best_text = result['text']
                    best_conf = result['confidence']
                    best_method = f"region_{region_info['name']}_{result['method']}"

            # 方法2: 如果没找到区域，使用固定区域
            if len(best_text) < 3:
                for y_start_ratio, y_end_ratio in [
                    (0.84, 0.90),  # 84-90% 是字幕常见位置
                    (0.82, 0.92),  # 扩展区域
                    (0.80, 0.93),
                    (0.85, 0.95),
                ]:
                    y_start = int(height * y_start_ratio)
                    y_end = int(height * y_end_ratio)
                    region = image[y_start:y_end, :]

                    result = self._ocr_region_with_configs(region, lang)
                    if result['confidence'] > best_conf and len(result['text'].strip()) > 2:
                        best_text = result['text']
                        best_conf = result['confidence']
                        best_method = f"fixed_{y_start_ratio:.0%}_{result['method']}"

            # 清理文本
            cleaned = self._clean_text(best_text)

            return {
                "text": cleaned,
                "confidence": best_conf,
                "method": best_method,
                "regions_found": len(subtitle_regions)
            }
        except Exception as e:
            print(f"字幕检测失败: {e}")
            return {"text": "", "confidence": 0.0, "method": "error"}

    def _find_subtitle_regions(self, image: np.ndarray) -> List[Dict]:
        """找到图像中可能的字幕区域"""
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        regions = []

        # 策略1: 找底部白条（字幕条）
        # 检查 80-95% 区域的白像素行（降低阈值到100，因为字幕可能不是很亮）
        bottom_80 = int(height * 0.80)
        bottom_95 = int(height * 0.95)

        white_rows = []
        for y in range(bottom_80, bottom_95):
            white_count = np.sum(gray[y, :] > 100)  # 降低阈值从180到100
            white_ratio = white_count / width
            if white_ratio > 0.04:  # 降低阈值从0.05到0.04
                white_rows.append((y, white_count, white_ratio))

        # 找出连续区域
        if white_rows:
            continuous_ranges = []
            start_y = white_rows[0][0]
            prev_y = start_y

            for y, count, ratio in white_rows[1:]:
                if y - prev_y > 5:
                    if prev_y - start_y > 3:
                        continuous_ranges.append((start_y, prev_y))
                    start_y = y
                prev_y = y

            if prev_y - start_y > 3:
                continuous_ranges.append((start_y, prev_y))

            for start, end in continuous_ranges:
                regions.append({
                    'name': 'bottom_white',
                    'y_start': max(0, start - 5),
                    'y_end': min(height, end + 5),
                    'score': (end - start) * np.mean([r[2] for r in white_rows if start <= r[0] <= end])
                })

        # 策略2: 使用连通域分析找文字区域
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        inverted = cv2.bitwise_not(binary)

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(inverted, connectivity=8)

        for i in range(1, num_labels):
            x, y, w, h, area = stats[i]

            # 过滤条件
            if area < 200:
                continue
            if h > height * 0.2:
                continue
            if w < width * 0.1:  # 宽的文本区域
                continue

            # 只考虑底部区域
            if y > height * 0.70 and y < height * 0.95:
                aspect = w / max(h, 1)
                if aspect > 2:  # 扁平的区域
                    regions.append({
                        'name': 'connected',
                        'y_start': max(0, y - 5),
                        'y_end': min(height, y + h + 5),
                        'score': area * aspect
                    })

        # 按得分排序
        regions.sort(key=lambda x: x.get('score', 0), reverse=True)
        return regions[:5]  # 返回前5个

    def _ocr_region_with_configs(self, region: np.ndarray, lang: str) -> Dict:
        """使用多种配置对区域进行 OCR"""
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape

        best_text = ""
        best_conf = 0.0
        best_method = ""

        # 定义多种预处理和 OCR 配置组合
        configs = [
            # 预处理方法 + PSM + 语言
            ('inverted_otsu', 'psm6', 'chi_sim+eng'),
            ('normal_otsu', 'psm6', 'chi_sim+eng'),
            ('inverted_otsu', 'psm7', 'chi_sim+eng'),
            ('normal_otsu', 'psm7', 'chi_sim+eng'),
            ('inverted_adaptive', 'psm6', 'chi_sim+eng'),
            ('inverted_otsu', 'psm6', 'eng'),
            ('inverted_otsu', 'psm7', 'eng'),
        ]

        for preprocess, psm, ocr_lang in configs:
            try:
                # 预处理
                if preprocess == 'inverted_otsu':
                    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    processed = cv2.bitwise_not(binary)
                elif preprocess == 'normal_otsu':
                    _, processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                elif preprocess == 'inverted_adaptive':
                    blur = cv2.GaussianBlur(gray, (5, 5), 0)
                    processed = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                    processed = cv2.bitwise_not(processed)
                else:
                    _, processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                # 形态学处理 - 稍微膨胀文字
                kernel = np.ones((1, 2), np.uint8)
                processed = cv2.dilate(processed, kernel, iterations=1)

                # OCR
                pil_img = Image.fromarray(processed)
                config = f'--oem 3 --{psm}'
                text = pytesseract.image_to_string(pil_img, lang=ocr_lang, config=config)

                # 获取置信度
                data = pytesseract.image_to_data(pil_img, lang=ocr_lang, output_type=pytesseract.Output.DICT)
                confidences = [float(c) for c in data['conf'] if float(c) > 0]
                avg_conf = sum(confidences) / len(confidences) if confidences else 0

                # 清理文本
                cleaned = self._clean_text(text)

                # 选择最佳结果
                score = len(cleaned) * 1.0 + avg_conf * 0.1
                best_score = len(best_text) * 1.0 + best_conf * 0.1

                if score > best_score:
                    best_text = cleaned
                    best_conf = avg_conf
                    best_method = f"{preprocess}_{psm}_{ocr_lang}"

            except Exception as e:
                continue

        return {
            "text": best_text,
            "confidence": best_conf,
            "method": best_method
        }

    def _clean_text(self, text: str) -> str:
        """清理 OCR 识别的文本"""
        import re

        if not text:
            return ""

        # 移除每行首尾空白
        lines = [line.strip() for line in text.split('\n')]

        # 过滤空行
        lines = [line for line in lines if len(line) > 0]

        # 移除纯符号行
        lines = [line for line in lines if not re.match(r'^[_\-=~|]{3,}$', line)]

        # 计算有意义的字符
        cleaned_lines = []
        for line in lines:
            meaningful = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf a-zA-Z0-9]', line)
            if len(meaningful) / max(len(line), 1) > 0.3:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def extract_text_from_image(self, image_path: str, lang: str = 'chi_sim+eng') -> Dict:
        """从图像中提取文字"""
        if not TESSERACT_AVAILABLE:
            return {"text": "", "boxes": [], "confidence": 0.0}

        try:
            image = cv2.imread(image_path)
            if image is None:
                return {"text": "", "boxes": [], "confidence": 0.0}

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            best_text = ""
            best_conf = 0.0

            # 尝试多种预处理
            for preprocess_name, preprocess in [
                ('otsu', self._preprocess_otsu),
                ('inverted', self._preprocess_inverted),
                ('adaptive', self._preprocess_adaptive),
            ]:
                processed = preprocess(gray)
                pil_img = Image.fromarray(processed)

                config = '--oem 3 --psm 6'
                text = pytesseract.image_to_string(pil_img, lang=lang, config=config)

                data = pytesseract.image_to_data(pil_img, lang=lang, output_type=pytesseract.Output.DICT)
                confidences = [float(c) for c in data['conf'] if float(c) > 0]
                avg_conf = sum(confidences) / len(confidences) if confidences else 0

                if len(text.strip()) > len(best_text):
                    best_text = text.strip()
                    best_conf = avg_conf

            return {
                "text": best_text,
                "boxes": [],
                "confidence": best_conf
            }
        except Exception as e:
            return {"text": "", "boxes": [], "confidence": 0.0}

    def _preprocess_otsu(self, gray: np.ndarray) -> np.ndarray:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def _preprocess_inverted(self, gray: np.ndarray) -> np.ndarray:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.bitwise_not(binary)

    def _preprocess_adaptive(self, gray: np.ndarray) -> np.ndarray:
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        return cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    def extract_text_from_images(self, image_paths: List[str], lang: str = 'chi_sim+eng') -> List[Dict]:
        """批量从多个图像中提取文字"""
        results = []
        for image_path in image_paths:
            result = self.extract_text_from_image(image_path, lang)
            result["image_path"] = image_path
            results.append(result)
        return results

    def detect_subtitles(self, image_path: str, lang: str = 'chi_sim+eng') -> Dict:
        """检测图像中的字幕"""
        return self.detect_subtitle_from_frame(image_path, lang)

    def filter_meaningful_text(self, ocr_results: List[Dict], min_length: int = 2,
                               min_confidence: float = 30.0) -> List[Dict]:
        """过滤有意义的 OCR 结果"""
        filtered = []
        for result in ocr_results:
            text = result.get('text', '').strip()
            confidence = result.get('confidence', 0)

            if len(text) < min_length:
                continue
            if confidence < min_confidence:
                continue

            # 检查是否有意义
            import re
            meaningful = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf a-zA-Z0-9]', text)
            if len(meaningful) / max(len(text), 1) < 0.3:
                continue

            filtered.append(result)
        return filtered


# 创建服务实例
ocr_service = OCRService()


# 导出函数
def extract_text_from_image(image_path: str, lang: str = 'chi_sim+eng') -> Dict:
    return ocr_service.extract_text_from_image(image_path, lang)

def extract_text_from_images(image_paths: List[str], lang: str = 'chi_sim+eng') -> List[Dict]:
    return ocr_service.extract_text_from_images(image_paths, lang)

def detect_subtitles(image_path: str, lang: str = 'chi_sim+eng') -> Dict:
    return ocr_service.detect_subtitles(image_path, lang)

def filter_meaningful_text(ocr_results: List[Dict], min_length: int = 2,
                           min_confidence: float = 30.0) -> List[Dict]:
    return ocr_service.filter_meaningful_text(ocr_results, min_length, min_confidence)


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