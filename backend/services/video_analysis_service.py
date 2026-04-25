import os
import cv2
import ffmpeg
import numpy as np
from typing import List, Dict, Tuple
import tempfile
import shutil

class VideoAnalysisService:
    def __init__(self):
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def extract_screenshots_by_interval(self, video_path: str, interval: int = 5) -> List[Dict]:
        """
        根据时间间隔提取视频截图
        
        Args:
            video_path: 视频文件路径
            interval: 截图间隔（秒）
            
        Returns:
            包含截图信息的列表
        """
        screenshots = []
        
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"无法打开视频文件: {video_path}")
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        # 计算每隔多少帧截图一次
        frame_interval = int(fps * interval)
        current_frame = 0
        screenshot_count = 0
        
        while current_frame < frame_count:
            # 设置当前帧位置
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            
            # 读取帧
            ret, frame = cap.read()
            if not ret:
                break
            
            # 计算当前时间
            current_time = current_frame / fps
            
            # 保存截图
            screenshot_path = self._save_screenshot(frame, video_path, current_time, screenshot_count)
            
            # 添加截图信息
            screenshots.append({
                "path": screenshot_path,
                "time": current_time,
                "frame": current_frame,
                "index": screenshot_count
            })
            
            # 增加帧计数
            current_frame += frame_interval
            screenshot_count += 1
        
        cap.release()
        return screenshots
    
    def extract_screenshots_by_scene_change(self, video_path: str, threshold: float = 30.0) -> List[Dict]:
        """
        根据场景变化提取视频截图
        
        Args:
            video_path: 视频文件路径
            threshold: 场景变化阈值
            
        Returns:
            包含截图信息的列表
        """
        screenshots = []
        
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"无法打开视频文件: {video_path}")
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 读取第一帧
        ret, prev_frame = cap.read()
        if not ret:
            cap.release()
            return screenshots
        
        # 转换为灰度图
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        
        # 保存第一帧
        screenshot_path = self._save_screenshot(prev_frame, video_path, 0, 0)
        screenshots.append({
            "path": screenshot_path,
            "time": 0,
            "frame": 0,
            "index": 0
        })
        
        screenshot_count = 1
        current_frame = 1
        
        while current_frame < frame_count:
            # 读取当前帧
            ret, current_frame_img = cap.read()
            if not ret:
                break
            
            # 转换为灰度图
            current_gray = cv2.cvtColor(current_frame_img, cv2.COLOR_BGR2GRAY)
            
            # 计算帧差异
            diff = cv2.absdiff(prev_gray, current_gray)
            mean_diff = np.mean(diff)
            
            # 如果差异超过阈值，保存截图
            if mean_diff > threshold:
                current_time = current_frame / fps
                screenshot_path = self._save_screenshot(current_frame_img, video_path, current_time, screenshot_count)
                screenshots.append({
                    "path": screenshot_path,
                    "time": current_time,
                    "frame": current_frame,
                    "index": screenshot_count
                })
                screenshot_count += 1
                prev_gray = current_gray
            
            current_frame += 1
        
        cap.release()
        return screenshots
    
    def _save_screenshot(self, frame: np.ndarray, video_path: str, timestamp: float, index: int) -> str:
        """
        保存截图到文件
        
        Args:
            frame: 视频帧
            video_path: 视频文件路径
            timestamp: 时间戳
            index: 截图索引
            
        Returns:
            截图文件路径
        """
        # 获取视频文件名
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # 创建视频专用的截图目录
        video_screenshot_dir = os.path.join(self.screenshot_dir, video_name)
        os.makedirs(video_screenshot_dir, exist_ok=True)
        
        # 生成截图文件名
        filename = f"screenshot_{index:04d}_{timestamp:.2f}s.jpg"
        screenshot_path = os.path.join(video_screenshot_dir, filename)
        
        # 保存截图
        cv2.imwrite(screenshot_path, frame)
        
        return screenshot_path
    
    def get_video_info(self, video_path: str) -> Dict:
        """
        获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频信息字典
        """
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            
            if not video_stream:
                raise Exception("未找到视频流")
            
            return {
                "duration": float(video_stream.get('duration', 0)),
                "width": int(video_stream.get('width', 0)),
                "height": int(video_stream.get('height', 0)),
                "fps": eval(video_stream.get('r_frame_rate', '0/1')),
                "codec": video_stream.get('codec_name', ''),
                "bit_rate": video_stream.get('bit_rate', 0)
            }
        except Exception as e:
            # 回退到OpenCV方法
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception(f"无法打开视频文件: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            cap.release()
            
            return {
                "duration": frame_count / fps if fps > 0 else 0,
                "width": width,
                "height": height,
                "fps": fps,
                "codec": "unknown",
                "bit_rate": 0
            }
    
    def clean_screenshots(self, video_path: str):
        """
        清理视频的截图
        
        Args:
            video_path: 视频文件路径
        """
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        video_screenshot_dir = os.path.join(self.screenshot_dir, video_name)
        
        if os.path.exists(video_screenshot_dir):
            shutil.rmtree(video_screenshot_dir)

# 创建服务实例
video_analysis_service = VideoAnalysisService()

# 导出函数
def extract_screenshots(video_path: str, method: str = "interval", interval: int = 5, threshold: float = 30.0) -> List[Dict]:
    """
    提取视频截图
    
    Args:
        video_path: 视频文件路径
        method: 提取方法 (interval 或 scene)
        interval: 截图间隔（秒）
        threshold: 场景变化阈值
        
    Returns:
        包含截图信息的列表
    """
    if method == "interval":
        return video_analysis_service.extract_screenshots_by_interval(video_path, interval)
    elif method == "scene":
        return video_analysis_service.extract_screenshots_by_scene_change(video_path, threshold)
    else:
        raise Exception(f"不支持的提取方法: {method}")

def get_video_info(video_path: str) -> Dict:
    """
    获取视频信息
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        视频信息字典
    """
    return video_analysis_service.get_video_info(video_path)

def clean_screenshots(video_path: str):
    """
    清理视频的截图
    
    Args:
        video_path: 视频文件路径
    """
    video_analysis_service.clean_screenshots(video_path)
