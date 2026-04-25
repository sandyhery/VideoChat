import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.ocr_service import extract_text_from_image

# 测试 OCR 功能
def test_ocr():
    print("测试 OCR 功能...")
    
    # 检查是否有测试图片
    test_image_path = "test_image.jpg"
    if not os.path.exists(test_image_path):
        print(f"测试图片不存在: {test_image_path}")
        print("请在项目根目录创建一个包含文字的测试图片 test_image.jpg")
        return
    
    try:
        result = extract_text_from_image(test_image_path)
        print(f"OCR 结果: {result}")
        print(f"提取的文字: {result['text']}")
        print(f"置信度: {result['confidence']}")
        print(f"文字框数量: {len(result['boxes'])}")
        print("OCR 测试成功！")
    except Exception as e:
        print(f"OCR 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ocr()
