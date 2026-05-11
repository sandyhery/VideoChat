"""
字幕服务模块
支持：
1. 提取视频内置字幕轨道
2. 优化的OCR字幕检测
3. 从转录生成字幕文件
"""

import os
import json
import subprocess
import tempfile
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class SubtitleService:
    """字幕服务类"""

    def __init__(self):
        self.ffmpeg_probe_path = "ffprobe"
        self.ffmpeg_path = "ffmpeg"

    def extract_subtitle_tracks(self, video_path: str) -> List[Dict]:
        """
        提取视频内置字幕轨道

        Args:
            video_path: 视频文件路径

        Returns:
            字幕轨道列表
        """
        try:
            # 使用 ffprobe 获取视频信息
            cmd = [
                self.ffmpeg_probe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                '-select_streams', 's',
                video_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"[extract_subtitle_tracks] ffprobe error: {result.stderr}")
                return []

            probe_data = json.loads(result.stdout)
            streams = probe_data.get('streams', [])

            subtitle_tracks = []
            for i, stream in enumerate(streams):
                track_info = {
                    'index': i,
                    'codec_name': stream.get('codec_name', 'unknown'),
                    'codec_long_name': stream.get('codec_long_name', ''),
                    'tags': stream.get('tags', {}),
                    'language': stream.get('tags', {}).get('language', 'unknown'),
                    'title': stream.get('tags', {}).get('title', ''),
                }
                subtitle_tracks.append(track_info)

            print(f"[extract_subtitle_tracks] Found {len(subtitle_tracks)} subtitle tracks")
            return subtitle_tracks

        except subprocess.TimeoutExpired:
            print("[extract_subtitle_tracks] ffprobe timeout")
            return []
        except Exception as e:
            print(f"[extract_subtitle_tracks] Error: {e}")
            return []

    def extract_subtitle_track(self, video_path: str, track_index: int = 0, output_format: str = 'srt') -> Optional[str]:
        """
        提取指定字幕轨道

        Args:
            video_path: 视频文件路径
            track_index: 字幕轨道索引
            output_format: 输出格式 (srt, ass, vtt)

        Returns:
            字幕文件路径，失败返回 None
        """
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as f:
                output_path = f.name

            # 使用 ffmpeg 提取字幕
            cmd = [
                self.ffmpeg_path,
                '-y',  # 覆盖输出文件
                '-i', video_path,
                '-map', f'0:s:{track_index}',
                '-f', output_format,
                output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                print(f"[extract_subtitle_track] ffmpeg error: {result.stderr}")
                if os.path.exists(output_path):
                    os.unlink(output_path)
                return None

            print(f"[extract_subtitle_track] Extracted to {output_path}")
            return output_path

        except Exception as e:
            print(f"[extract_subtitle_track] Error: {e}")
            return None

    def generate_srt_from_transcription(self, transcription: List[Dict], output_path: Optional[str] = None) -> str:
        """
        从转录结果生成 SRT 格式字幕

        Args:
            transcription: 转录结果列表 [{start, end, text}, ...]
            output_path: 输出文件路径

        Returns:
            生成的字幕文件路径
        """
        if not transcription:
            raise ValueError("转录结果为空")

        if output_path is None:
            with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as f:
                output_path = f.name

        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(transcription, 1):
                start_time = self._seconds_to_srt_time(segment.get('start', 0))
                end_time = self._seconds_to_srt_time(segment.get('end', 0))
                text = segment.get('text', '').strip()

                # SRT 格式：序号\n开始时间 --> 结束时间\n文本\n\n
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

        print(f"[generate_srt_from_transcription] Generated {output_path}")
        return output_path

    def generate_vtt_from_transcription(self, transcription: List[Dict], output_path: Optional[str] = None) -> str:
        """
        从转录结果生成 WebVTT 格式字幕

        Args:
            transcription: 转录结果列表 [{start, end, text}, ...]
            output_path: 输出文件路径

        Returns:
            生成的字幕文件路径
        """
        if not transcription:
            raise ValueError("转录结果为空")

        if output_path is None:
            with tempfile.NamedTemporaryFile(suffix='.vtt', delete=False) as f:
                output_path = f.name

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for i, segment in enumerate(transcription, 1):
                start_time = self._seconds_to_vtt_time(segment.get('start', 0))
                end_time = self._seconds_to_vtt_time(segment.get('end', 0))
                text = segment.get('text', '').strip()

                # VTT 格式：序号\n开始时间 --> 结束时间\n文本\n\n
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

        print(f"[generate_vtt_from_transcription] Generated {output_path}")
        return output_path

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _seconds_to_vtt_time(self, seconds: float) -> str:
        """将秒数转换为 VTT 时间格式 (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def detect_subtitle_regions(self, image) -> List[Dict]:
        """
        检测图像中可能的字幕区域
        改进版：检测多个可能的字幕区域

        Args:
            image: cv2 图像数组

        Returns:
            可能的字幕区域列表 [{'region': (y1, y2, x1, x2), 'confidence': float}, ...]
        """
        try:
            import cv2
            import numpy as np

            height, width = image.shape[:2]

            # 可能的字幕区域配置
            regions = [
                {'name': '底部', 'y_start': 0.75, 'y_end': 1.0, 'x_start': 0.0, 'x_end': 1.0},
                {'name': '顶部', 'y_start': 0.0, 'y_end': 0.15, 'x_start': 0.0, 'x_end': 1.0},
                {'name': '全屏', 'y_start': 0.0, 'y_end': 1.0, 'x_start': 0.0, 'x_end': 1.0},
                {'name': '底部中央', 'y_start': 0.8, 'y_end': 1.0, 'x_start': 0.15, 'x_end': 0.85},
                {'name': '底部上方', 'y_start': 0.65, 'y_end': 0.85, 'x_start': 0.0, 'x_end': 1.0},
            ]

            detected_regions = []

            for region_config in regions:
                y1 = int(height * region_config['y_start'])
                y2 = int(height * region_config['y_end'])
                x1 = int(width * region_config['x_start'])
                x2 = int(width * region_config['x_end'])

                region = image[y1:y2, x1:x2]

                # 检查区域是否有文字特征
                gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
                # 二值化
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                # 计算文字密度（白色像素比例）
                white_ratio = np.sum(binary == 255) / binary.size

                # 如果白色像素比例在合理范围内，认为是字幕区域
                if 0.01 < white_ratio < 0.5:
                    detected_regions.append({
                        'region': {
                            'y_start': region_config['y_start'],
                            'y_end': region_config['y_end'],
                            'x_start': region_config['x_start'],
                            'x_end': region_config['x_end'],
                            'pixel_y1': y1,
                            'pixel_y2': y2,
                            'pixel_x1': x1,
                            'pixel_x2': x2,
                        },
                        'name': region_config['name'],
                        'confidence': white_ratio,
                        'white_ratio': float(white_ratio)
                    })

            # 按置信度排序
            detected_regions.sort(key=lambda x: x['confidence'], reverse=True)

            return detected_regions

        except Exception as e:
            print(f"[detect_subtitle_regions] Error: {e}")
            return []

    def get_all_subtitle_sources(self, video_path: str, transcription: List[Dict] = None) -> Dict:
        """
        获取视频所有可用字幕来源

        Args:
            video_path: 视频文件路径
            transcription: 转录结果（可选）

        Returns:
            {
                'embedded_tracks': [...],  # 内置字幕轨道
                'has_transcription': bool,   # 是否有转录结果
                'can_generate_subtitle': bool # 是否可以生成字幕
            }
        """
        result = {
            'embedded_tracks': self.extract_subtitle_tracks(video_path),
            'has_transcription': transcription is not None and len(transcription) > 0,
            'can_generate_subtitle': transcription is not None and len(transcription) > 0,
        }
        return result


# 模块级实例
subtitle_service = SubtitleService()


def extract_subtitle_tracks(video_path: str) -> List[Dict]:
    """提取视频内置字幕轨道"""
    return subtitle_service.extract_subtitle_tracks(video_path)


def extract_subtitle_track(video_path: str, track_index: int = 0, output_format: str = 'srt') -> Optional[str]:
    """提取指定字幕轨道"""
    return subtitle_service.extract_subtitle_track(video_path, track_index, output_format)


def generate_srt_from_transcription(transcription: List[Dict], output_path: Optional[str] = None) -> str:
    """从转录生成 SRT 字幕"""
    return subtitle_service.generate_srt_from_transcription(transcription, output_path)


def generate_vtt_from_transcription(transcription: List[Dict], output_path: Optional[str] = None) -> str:
    """从转录生成 VTT 字幕"""
    return subtitle_service.generate_vtt_from_transcription(transcription, output_path)


def get_all_subtitle_sources(video_path: str, transcription: List[Dict] = None) -> Dict:
    """获取所有字幕来源"""
    return subtitle_service.get_all_subtitle_sources(video_path, transcription)
