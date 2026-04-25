import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from services.video_analysis_service import extract_screenshots, get_video_info
from services.ocr_service import extract_text_from_images, detect_subtitles
from services.ai_service import generate_summary, generate_mindmap
import asyncio

class MultimodalAnalysisService:
    def __init__(self):
        self.analysis_results_dir = "analysis_results"
        os.makedirs(self.analysis_results_dir, exist_ok=True)
        self.cache = {}  # 缓存分析结果
        self.cache_max_size = 10  # 缓存最大大小
    
    async def analyze_video(self, video_path: str, transcription: List[Dict], 
                          screenshot_method: str = "interval", 
                          screenshot_interval: int = 5, 
                          screenshot_threshold: float = 30.0,
                          use_cache: bool = True) -> Dict:
        """
        对视频进行多模态分析
        
        Args:
            video_path: 视频文件路径
            transcription: 音频转录结果
            screenshot_method: 截图方法 (interval 或 scene)
            screenshot_interval: 截图间隔（秒）
            screenshot_threshold: 场景变化阈值
            use_cache: 是否使用缓存结果
            
        Returns:
            多模态分析结果
        """
        try:
            print(f"开始分析视频: {video_path}")
            
            # 生成缓存键
            cache_key = f"{video_path}_{screenshot_method}_{screenshot_interval}_{screenshot_threshold}"
            
            # 检查缓存
            if use_cache and cache_key in self.cache:
                print("使用缓存结果")
                return self.cache[cache_key]
            elif not use_cache:
                print("跳过缓存，重新分析")
            
            # 检查视频文件是否存在
            if not os.path.exists(video_path):
                raise Exception(f"视频文件不存在: {video_path}")
            
            # 1. 获取视频信息
            print("获取视频信息...")
            video_info = get_video_info(video_path)
            print(f"视频信息: {video_info}")
            
            # 2. 提取视频截图
            print("提取视频截图...")
            screenshots = extract_screenshots(
                video_path, 
                method=screenshot_method, 
                interval=screenshot_interval, 
                threshold=screenshot_threshold
            )
            print(f"提取了 {len(screenshots)} 张截图")
            
            # 3. 对截图进行OCR分析（并行处理）
            print("进行OCR分析...")
            image_paths = [screenshot["path"] for screenshot in screenshots]
            
            try:
                ocr_results = extract_text_from_images(image_paths)
                print(f"OCR分析完成，处理了 {len(ocr_results)} 张图片")
            except Exception as e:
                print(f"OCR分析失败: {e}")
                # 如果OCR失败，使用空结果继续
                ocr_results = []
                for screenshot in screenshots:
                    ocr_results.append({
                        "text": "",
                        "boxes": [],
                        "confidence": 0.0,
                        "image_path": screenshot["path"]
                    })
                print(f"创建了 {len(ocr_results)} 个空OCR结果")
            
            # 4. 检测字幕（并行处理）
            print("检测字幕...")
            subtitle_results = []
            for screenshot in screenshots:
                try:
                    subtitle = detect_subtitles(screenshot["path"])
                    if subtitle["text"]:
                        subtitle_results.append({
                            "time": screenshot["time"],
                            "text": subtitle["text"],
                            "confidence": subtitle["confidence"]
                        })
                except Exception as e:
                    # 如果字幕检测失败，继续下一个
                    pass
            print(f"检测到 {len(subtitle_results)} 处字幕")
            
            # 5. 整合数据
            print("整合数据...")
            multimodal_data = self._integrate_data(
                video_info, 
                screenshots, 
                ocr_results, 
                subtitle_results, 
                transcription
            )
            
            # 6. 生成分析结果
            print("生成分析结果...")
            analysis_result = await self._generate_analysis(multimodal_data, video_path)
            
            # 7. 保存分析结果
            print("保存分析结果...")
            result_path = self._save_analysis_result(video_path, analysis_result)
            
            # 构建结果
            result = {
                "status": "success",
                "video_info": video_info,
                "screenshot_count": len(screenshots),
                "ocr_results": ocr_results,
                "subtitle_results": subtitle_results,
                "analysis": analysis_result,
                "result_path": result_path
            }
            
            # 更新缓存
            if len(self.cache) >= self.cache_max_size:
                # 删除最早的缓存
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
            self.cache[cache_key] = result
            
            print("多模态分析完成！")
            return result
        except Exception as e:
            print(f"多模态分析失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"多模态分析失败: {str(e)}")
    
    def _integrate_data(self, video_info: Dict, screenshots: List[Dict], 
                       ocr_results: List[Dict], subtitle_results: List[Dict], 
                       transcription: List[Dict]) -> Dict:
        """
        整合多模态数据
        
        Args:
            video_info: 视频信息
            screenshots: 截图信息
            ocr_results: OCR结果
            subtitle_results: 字幕结果
            transcription: 音频转录结果
            
        Returns:
            整合后的数据
        """
        # 按时间顺序整合数据
        time_series_data = []
        
        # 添加转录数据
        for segment in transcription:
            time_series_data.append({
                "type": "transcription",
                "time": segment['start'],
                "end_time": segment['end'],
                "content": segment['text']
            })
        
        # 添加截图数据
        for i, screenshot in enumerate(screenshots):
            ocr_result = next((ocr for ocr in ocr_results if ocr["image_path"] == screenshot["path"]), None)
            time_series_data.append({
                "type": "screenshot",
                "time": screenshot["time"],
                "content": {
                    "path": screenshot["path"],
                    "ocr_text": ocr_result["text"] if ocr_result else ""
                }
            })
        
        # 添加字幕数据
        for subtitle in subtitle_results:
            time_series_data.append({
                "type": "subtitle",
                "time": subtitle["time"],
                "content": subtitle["text"]
            })
        
        # 按时间排序
        time_series_data.sort(key=lambda x: x["time"])
        
        return {
            "video_info": video_info,
            "time_series_data": time_series_data,
            "screenshots": screenshots,
            "ocr_results": ocr_results,
            "subtitle_results": subtitle_results,
            "transcription": transcription
        }
    
    async def _generate_analysis(self, multimodal_data: Dict, video_path: str) -> Dict:
        """
        生成多模态分析结果
        
        Args:
            multimodal_data: 整合后的多模态数据
            video_path: 视频文件路径
            
        Returns:
            分析结果
        """
        # 准备分析提示
        prompt = self._prepare_analysis_prompt(multimodal_data, video_path)
        
        # 获取文件名
        filename = os.path.basename(video_path)
        
        # 生成分析总结
        summary_chunks = []
        async for chunk in generate_summary(prompt, filename):
            summary_chunks.append(chunk)
        summary = "".join(summary_chunks)
        
        # 生成思维导图
        mindmap = await generate_mindmap(prompt, filename)
        
        return {
            "summary": summary,
            "mindmap": mindmap,
            "analysis_time": datetime.now().isoformat()
        }
    
    def _prepare_analysis_prompt(self, multimodal_data: Dict, video_path: str) -> str:
        """
        准备分析提示

        Args:
            multimodal_data: 整合后的多模态数据
            video_path: 视频文件路径

        Returns:
            分析提示
        """
        # 从文件名中提取有意义的信息
        filename = os.path.basename(video_path)
        import re
        clean_filename = re.sub(r'\.\w+$', '', filename)
        clean_filename = re.sub(r'^\d+[_\-]', '', clean_filename)

        prompt = f"""你是一个专业的视频内容分析专家。请对以下视频内容进行全面、深入的多模态分析。

重要提示：视频文件名为 "{clean_filename}"，这个文件名本身就是一个很好的概括，请在分析时充分考虑这个信息。

"""

        # 添加视频信息
        video_info = multimodal_data["video_info"]
        prompt += f"视频基本信息：\n"
        prompt += f"- 时长：{video_info['duration']:.2f}秒\n"
        prompt += f"- 分辨率：{video_info['width']}x{video_info['height']}\n"
        prompt += f"- 帧率：{video_info['fps']:.2f}fps\n\n"

        # 添加转录内容
        transcription = multimodal_data["transcription"]
        if transcription:
            prompt += "=" * 50 + "\n"
            prompt += "【音频转录内容】\n"
            prompt += "=" * 50 + "\n"
            for segment in transcription:
                prompt += f"[{segment['start']:.2f}s-{segment['end']:.2f}s] {segment['text']}\n"
            prompt += "\n"

        # 添加OCR内容（移除截断限制，完整保留）
        ocr_results = multimodal_data["ocr_results"]
        ocr_texts = [ocr["text"] for ocr in ocr_results if ocr.get("text")]
        if ocr_texts:
            prompt += "=" * 50 + "\n"
            prompt += "【图像文字识别内容（OCR）】\n"
            prompt += "=" * 50 + "\n"
            for i, ocr in enumerate(ocr_results):
                if ocr.get("text"):
                    screenshot = next((s for s in multimodal_data["screenshots"] if s["path"] == ocr["image_path"]), None)
                    time_str = f"[{screenshot['time']:.2f}s]" if screenshot else f"[截图{i+1}]"
                    # 移除截断限制，完整保留OCR内容
                    prompt += f"{time_str}: {ocr['text']}\n\n"
            prompt += "\n"

        # 添加字幕内容
        subtitle_results = multimodal_data["subtitle_results"]
        if subtitle_results:
            prompt += "=" * 50 + "\n"
            prompt += "【字幕内容】\n"
            prompt += "=" * 50 + "\n"
            for subtitle in subtitle_results:
                prompt += f"[{subtitle['time']:.2f}s] {subtitle['text']}\n"
            prompt += "\n"

        # 增强的分析框架
        prompt += "=" * 50 + "\n"
        prompt += "【分析要求】\n"
        prompt += "=" * 50 + "\n"
        prompt += """请基于以上音视频转录、图像文字（OCR）和字幕等多模态信息，进行全面深入的分析：

## 分析框架（请按此结构输出）：

### 1. 内容主题分析
- 视频的核心主题是什么
- 主题的切入角度和论述逻辑
- 与文件名的关联度

### 2. 核心内容要点
- 列出3-5个核心要点
- 每个要点包含：观点、论据、关键引用
- 保留重要数据和事实

### 3. 视觉与语言关联
- OCR内容与音频转录的对应关系
- 板书/PPT内容与口述内容的互补
- 视觉元素传达的关键信息

### 4. 关键引用与金句
- 视频中的重要原话
- 核心概念和定义
- 值得记录的关键论述

### 5. 总结与评价
- 内容的价值和意义
- 适用场景和受众
- 可能的延伸应用

请确保分析准确、深入、逻辑清晰。"""

        return prompt
    
    def _save_analysis_result(self, video_path: str, analysis_result: Dict) -> str:
        """
        保存分析结果
        
        Args:
            video_path: 视频文件路径
            analysis_result: 分析结果
            
        Returns:
            保存路径
        """
        # 获取视频文件名
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # 创建视频专用的分析结果目录
        video_result_dir = os.path.join(self.analysis_results_dir, video_name)
        os.makedirs(video_result_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{timestamp}.json"
        result_path = os.path.join(video_result_dir, filename)
        
        # 保存结果
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        return result_path
    
    def get_analysis_history(self, video_path: str) -> List[str]:
        """
        获取视频的分析历史
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            分析结果文件路径列表
        """
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        video_result_dir = os.path.join(self.analysis_results_dir, video_name)
        
        if not os.path.exists(video_result_dir):
            return []
        
        # 获取所有分析结果文件
        result_files = [f for f in os.listdir(video_result_dir) if f.endswith('.json')]
        result_files.sort(reverse=True)  # 按时间倒序
        
        return [os.path.join(video_result_dir, f) for f in result_files]

# 创建服务实例
multimodal_service = MultimodalAnalysisService()

# 导出函数
async def analyze_video(video_path: str, transcription: List[Dict], 
                       screenshot_method: str = "interval", 
                       screenshot_interval: int = 5, 
                       screenshot_threshold: float = 30.0,
                       use_cache: bool = True) -> Dict:
    """
    对视频进行多模态分析
    
    Args:
        video_path: 视频文件路径
        transcription: 音频转录结果
        screenshot_method: 截图方法 (interval 或 scene)
        screenshot_interval: 截图间隔（秒）
        screenshot_threshold: 场景变化阈值
        use_cache: 是否使用缓存结果
        
        Returns:
        多模态分析结果
    """
    return await multimodal_service.analyze_video(
        video_path, 
        transcription, 
        screenshot_method, 
        screenshot_interval, 
        screenshot_threshold,
        use_cache
    )

def get_analysis_history(video_path: str) -> List[str]:
    """
    获取视频的分析历史
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        分析结果文件路径列表
    """
    return multimodal_service.get_analysis_history(video_path)
