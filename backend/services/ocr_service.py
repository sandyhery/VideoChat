import os
import cv2
from PIL import Image
import numpy as np
from typing import List, Dict, Tuple
import tempfile

# 尝试导入pytesseract，如果失败则使用降级方案
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("警告: pytesseract未安装，OCR功能将被禁用")

class OCRService:
    def __init__(self):
        # 配置Tesseract路径
        pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'
        pass
    
    def extract_text_from_image(self, image_path: str, lang: str = 'chi_sim+eng') -> Dict:
        """
        从图像中提取文字
        
        Args:
            image_path: 图像文件路径
            lang: 语言代码，默认中英文
            
        Returns:
            包含提取文字和详细信息的字典
        """
        if not TESSERACT_AVAILABLE:
            # 如果Tesseract不可用，返回空结果
            return {
                "text": "",
                "boxes": [],
                "confidence": 0.0
            }
        
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                raise Exception(f"无法读取图像: {image_path}")
            
            # 图像预处理
            processed_image = self._preprocess_image(image)
            
            # 使用PIL读取处理后的图像
            pil_image = Image.fromarray(processed_image)
            
            # 提取文字
            text = pytesseract.image_to_string(pil_image, lang=lang)
            
            # 提取详细信息
            details = pytesseract.image_to_data(pil_image, lang=lang, output_type=pytesseract.Output.DICT)
            
            # 处理详细信息
            boxes = []
            for i in range(len(details['text'])):
                if int(details['conf'][i]) > 60:  # 只保留置信度高的结果
                    (x, y, w, h) = (details['left'][i], details['top'][i], details['width'][i], details['height'][i])
                    boxes.append({
                        "text": details['text'][i].strip(),
                        "confidence": details['conf'][i],
                        "position": {
                            "x": x,
                            "y": y,
                            "width": w,
                            "height": h
                        }
                    })
            
            return {
                "text": text.strip(),
                "boxes": boxes,
                "confidence": self._calculate_average_confidence(details['conf'])
            }
        except Exception as e:
            print(f"OCR处理失败: {e}")
            # 降级处理：返回空结果
            return {
                "text": "",
                "boxes": [],
                "confidence": 0.0
            }
    
    def extract_text_from_images(self, image_paths: List[str], lang: str = 'chi_sim+eng') -> List[Dict]:
        """
        批量从多个图像中提取文字
        
        Args:
            image_paths: 图像文件路径列表
            lang: 语言代码，默认中英文
            
        Returns:
            包含每个图像提取结果的列表
        """
        results = []
        for image_path in image_paths:
            try:
                result = self.extract_text_from_image(image_path, lang)
                result["image_path"] = image_path
                results.append(result)
            except Exception as e:
                results.append({
                    "image_path": image_path,
                    "text": "",
                    "boxes": [],
                    "confidence": 0,
                    "error": str(e)
                })
        return results
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        图像预处理以提高OCR accuracy
        
        Args:
            image: 输入图像
            
        Returns:
            处理后的图像
        """
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 尝试多种预处理方法，选择最好的结果
        # 方法1: 标准预处理
        blurred1 = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh1 = cv2.threshold(blurred1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 方法2: 反转颜色（适合黑板文字）
        blurred2 = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh2 = cv2.threshold(blurred2, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh2 = cv2.bitwise_not(thresh2)
        
        # 方法3: 自适应阈值（适合不均匀光照）
        blurred3 = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh3 = cv2.adaptiveThreshold(blurred3, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY, 11, 2)
        
        # 返回方法1的结果，但我们可以在实际使用中尝试多种方法
        # 这里我们选择标准预处理，但对黑板文字特别优化
        # 检查是否是黑色背景白色文字（黑板特征）
        mean_gray = np.mean(gray)
        if mean_gray < 100:  # 暗背景，可能是黑板
            processed = thresh2  # 使用反转颜色
        else:
            processed = thresh1  # 使用标准预处理
        
        # 轻微膨胀操作，增强文字
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.dilate(processed, kernel, iterations=1)
        
        return processed
    
    def _calculate_average_confidence(self, confidences: List) -> float:
        """
        计算平均置信度
        
        Args:
            confidences: 置信度列表
            
        Returns:
            平均置信度
        """
        valid_confidences = [float(c) for c in confidences if c != '-1']
        if not valid_confidences:
            return 0.0
        return sum(valid_confidences) / len(valid_confidences)
    
    def detect_subtitles(self, image_path: str, lang: str = 'chi_sim+eng') -> Dict:
        """
        检测图像中的字幕
        
        Args:
            image_path: 图像文件路径
            lang: 语言代码，默认中英文
            
        Returns:
            包含字幕信息的字典
        """
        if not TESSERACT_AVAILABLE:
            # 如果Tesseract不可用，返回空结果
            return {
                "text": "",
                "boxes": [],
                "confidence": 0.0,
                "subtitle_region": {
                    "y_start": 0,
                    "y_end": 0,
                    "x_start": 0,
                    "x_end": 0
                }
            }
        
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                raise Exception(f"无法读取图像: {image_path}")
            
            # 截取图像底部区域（通常字幕位置）
            height, width = image.shape[:2]
            subtitle_region = image[int(height * 0.8):, :]  # 底部20%区域
            
            # 保存临时区域图像
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                cv2.imwrite(temp_file.name, subtitle_region)
                temp_path = temp_file.name
            
            # 提取文字
            result = self.extract_text_from_image(temp_path, lang)
            
            # 清理临时文件
            os.unlink(temp_path)
            
            # 添加区域信息
            result["subtitle_region"] = {
                "y_start": int(height * 0.8),
                "y_end": height,
                "x_start": 0,
                "x_end": width
            }
            
            return result
        except Exception as e:
            print(f"字幕检测失败: {e}")
            # 降级处理：返回空结果
            return {
                "text": "",
                "boxes": [],
                "confidence": 0.0,
                "subtitle_region": {
                    "y_start": 0,
                    "y_end": 0,
                    "x_start": 0,
                    "x_end": 0
                }
            }

# 创建服务实例
ocr_service = OCRService()

# 导出函数
def extract_text_from_image(image_path: str, lang: str = 'chi_sim+eng') -> Dict:
    """
    从图像中提取文字
    
    Args:
        image_path: 图像文件路径
        lang: 语言代码，默认中英文
        
    Returns:
        包含提取文字和详细信息的字典
    """
    return ocr_service.extract_text_from_image(image_path, lang)

def extract_text_from_images(image_paths: List[str], lang: str = 'chi_sim+eng') -> List[Dict]:
    """
    批量从多个图像中提取文字
    
    Args:
        image_paths: 图像文件路径列表
        lang: 语言代码，默认中英文
        
    Returns:
        包含每个图像提取结果的列表
    """
    return ocr_service.extract_text_from_images(image_paths, lang)

def detect_subtitles(image_path: str, lang: str = 'chi_sim+eng') -> Dict:
    """
    检测图像中的字幕
    
    Args:
        image_path: 图像文件路径
        lang: 语言代码，默认中英文
        
    Returns:
        包含字幕信息的字典
    """
    return ocr_service.detect_subtitles(image_path, lang)
