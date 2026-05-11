from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import tempfile
from datetime import datetime
from services.stt_service import transcribe_audio, stop_transcription, is_file_being_transcribed
from services.ai_service import generate_summary, generate_mindmap, chat_with_model, generate_detailed_summary, add_punctuation_and_segmentation
from services.multimodal_service import analyze_video
from services.subtitle_service import (
    extract_subtitle_tracks,
    extract_subtitle_track,
    generate_srt_from_transcription,
    generate_vtt_from_transcription,
    get_all_subtitle_sources
)
from models import ChatMessage, ChatRequest
import asyncio

app = FastAPI()

# 添加静态文件服务
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加一个变量来跟踪转录任务
transcription_task = None

class TextRequest(BaseModel):
    text: str
    filename: str = ""

class PunctuationRequest(BaseModel):
    transcription: List[dict]

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    global transcription_task
    try:
        # 保存上传的文件
        original_filename = file.filename  # 保存原始文件名
        file_path = f"uploads/{file.filename}"
        os.makedirs("uploads", exist_ok=True)

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 创建转录任务（传递文件名用于校准）
        transcription_task = asyncio.create_task(transcribe_audio(file_path, None, original_filename))
        try:
            transcription = await transcription_task
            transcription_task = None

            # 转录后处理：添加标点符号和分段
            if transcription and len(transcription) > 0:
                # 合并所有文本
                full_text = "\n".join([seg.get('text', '') for seg in transcription])
                print(f"[upload_file] 转录完成，共 {len(transcription)} 段，开始添加标点...")
                print(f"[upload_file] 原始文本长度: {len(full_text)}")
                if full_text.strip():
                    punctuated_text = await add_punctuation_and_segmentation(full_text)
                    print(f"[upload_file] 标点化完成，结果长度: {len(punctuated_text)}")
                    print(f"[upload_file] 标点化结果预览: {punctuated_text[:200]}...")
                    # 将标点化后的文本分割回多个片段（按换行分段）
                    segments = punctuated_text.split('\n')
                    print(f"[upload_file] 分段数量: {len(segments)}")
                    for i, seg_text in enumerate(segments):
                        if i < len(transcription):
                            transcription[i]['text'] = seg_text.strip()
                        elif seg_text.strip():
                            # 如果有额外的分段，添加新的转录片段
                            last_end = transcription[-1].get('end', 0) if transcription else 0
                            transcription.append({
                                "start": last_end,
                                "end": last_end + 1,
                                "text": seg_text.strip()
                            })
                else:
                    print("[upload_file] 文本为空，跳过标点处理")

            # 如果转录成功完成，直接返回结果
            return {"transcription": transcription}
            
        except asyncio.CancelledError:
            # 确保任务被正确取消
            if not transcription_task.cancelled():
                transcription_task.cancel()
            transcription_task = None
            # 返回特定的状态码和消息
            return JSONResponse(
                status_code=499,
                content={"status": "interrupted", "detail": "Transcription interrupted"}
            )
            
    except asyncio.CancelledError:
        # 返回特定的状态码和消息
        return JSONResponse(
            status_code=499,
            content={"status": "interrupted", "detail": "Transcription interrupted"}
        )
    except Exception as e:
        if transcription_task and not transcription_task.cancelled():
            transcription_task.cancel()
        transcription_task = None
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/summary")
async def get_summary(request: TextRequest):
    async def generate():
        async for chunk in generate_summary(request.text, request.filename):
            data = {"choices": [{"delta": {"content": chunk}}]}
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/mindmap")
async def get_mindmap(request: TextRequest):
    try:
        mindmap_json = await generate_mindmap(request.text, request.filename)
        return {"mindmap": mindmap_json}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/punctuation")
async def punctuation_transcription(request: PunctuationRequest):
    """为转录文本添加标点符号和分段"""
    try:
        if not request.transcription or len(request.transcription) == 0:
            raise HTTPException(status_code=400, detail="转录数据为空")

        # 合并所有文本
        full_text = "\n".join([seg.get('text', '') for seg in request.transcription])

        if not full_text.strip():
            return {"transcription": request.transcription}

        # 调用 AI 添加标点和分段
        punctuated_text = await add_punctuation_and_segmentation(full_text)

        # 将标点化后的文本分割回多个片段（按换行分段）
        segments = punctuated_text.split('\n')
        new_transcription = []

        for i, seg_text in enumerate(segments):
            if seg_text.strip():
                start = request.transcription[i].get('start', 0) if i < len(request.transcription) else 0
                end = request.transcription[i].get('end', start + 1) if i < len(request.transcription) else start + 1
                new_transcription.append({
                    "start": start,
                    "end": end,
                    "text": seg_text.strip()
                })

        return {"transcription": new_transcription}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def generate():
        async for chunk in chat_with_model(request.messages, request.context):
            data = {"choices": [{"delta": {"content": chunk}}]}
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/detailed-summary")
async def get_detailed_summary(request: TextRequest):
    async def generate():
        async for chunk in generate_detailed_summary(request.text, request.filename):
            data = {"choices": [{"delta": {"content": chunk}}]}
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/export/summary")
async def export_summary(summary: str = Body(...)):
    try:
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"summary_{timestamp}.md"
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as temp_file:
            temp_file.write(summary.encode('utf-8'))
            temp_file.flush()
            
            return FileResponse(
                path=temp_file.name,
                filename=filename,
                media_type="text/markdown",
                background=None
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export/mindmap")
async def export_mindmap(mindmap: dict = Body(...)):
    """导出思维导图为 xmind 格式"""
    try:
        import zipfile

        # 将 mindmap 数据转换为 xmind 格式
        # xmind 是 zip 格式，包含 content.json 文件

        def convert_to_xmind_content(mindmap_data):
            """将 jsMind 格式转换为 xmind 格式"""
            def process_node(node, parent_id=None):
                result = {
                    "id": node.get("id", ""),
                    "text": node.get("text", node.get("topic", "")),
                    "children": []
                }
                children = node.get("children", [])
                for child in children:
                    child_obj = process_node(child, result["id"])
                    result["children"].append(child_obj)
                return result

            root = mindmap_data.get("data", {})
            return {
                "root": process_node(root),
                "metadata": mindmap_data.get("meta", {})
            }

        xmind_content = convert_to_xmind_content(mindmap)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xmind") as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # 添加 content.json
                zip_file.writestr('content.json', json.dumps(xmind_content, ensure_ascii=False, indent=2))
                # 添加 metadata.xml
                metadata_xml = """<?xml version="1.0" encoding="UTF-8"?>
<xmeta xmlns="urn:xmind:xhtml:1.0">
  <creator>
    <name>VideoChat AI</name>
    <version>1.0</version>
  </creator>
  <timestamp>{}</timestamp>
</xmeta>""".format(datetime.now().isoformat())
                zip_file.writestr('metadata.xml', metadata_xml)

            temp_file.flush()

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mindmap_{timestamp}.xmind"

            return FileResponse(
                path=temp_file.name,
                filename=filename,
                media_type="application/x-xmind",
                background=None
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def generate_vtt(transcription):
    vtt_content = "WEBVTT\n\n"
    for segment in transcription:
        start = format_timestamp(segment['start'])
        end = format_timestamp(segment['end'])
        vtt_content += f"{start} --> {end}\n{segment['text']}\n\n"
    return vtt_content

def generate_srt(transcription):
    srt_content = ""
    for i, segment in enumerate(transcription, 1):
        start = format_timestamp(segment['start'], srt=True)
        end = format_timestamp(segment['end'], srt=True)
        srt_content += f"{i}\n{start} --> {end}\n{segment['text']}\n\n"
    return srt_content

def generate_txt(transcription):
    return "\n".join(segment['text'] for segment in transcription)

def format_timestamp(seconds, srt=False):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds - int(seconds)) * 1000)
    
    if srt:
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{msecs:03d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{msecs:03d}"

@app.post("/api/export/{format}")
async def export_transcription(format: str, transcription: List[dict]):
    if not transcription:
        raise HTTPException(status_code=400, detail="No transcription data provided")
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
            content = ""
            if format == "vtt":
                content = generate_vtt(transcription)
                mime_type = "text/vtt"
            elif format == "srt":
                content = generate_srt(transcription)
                mime_type = "application/x-subrip"
            elif format == "txt":
                content = generate_txt(transcription)
                mime_type = "text/plain"
            else:
                raise HTTPException(status_code=400, detail="Unsupported format")
            
            temp_file.write(content.encode('utf-8'))
            temp_file.flush()
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transcription_{timestamp}.{format}"
            
            # 返回文件
            return FileResponse(
                path=temp_file.name,
                filename=filename,
                media_type=mime_type,
                background=None  # 立即发送文件
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop-transcribe")
async def stop_transcribe():
    global transcription_task
    try:
        # 先设置停止标志
        stop_transcription()

        if transcription_task and not transcription_task.cancelled():
            # 取消正在进行的转录任务
            transcription_task.cancel()
            try:
                await asyncio.wait_for(transcription_task, timeout=0.5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
            transcription_task = None

        return {"message": "Transcription stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MultimodalAnalysisRequest(BaseModel):
    video_path: str
    transcription: list[dict]
    screenshot_method: str = "interval"
    screenshot_interval: int = 5
    screenshot_threshold: float = 30.0
    use_cache: bool = True
    chat_history: list = []  # 对话交互历史
    multimodal_result: dict = None  # 已执行的多模态分析结果，用于整合报告

@app.post("/api/multimodal-analysis")
async def multimodal_analysis(request: MultimodalAnalysisRequest):
    """多模态分析接口：分析视频截图、OCR识别、字幕检测"""
    try:
        # 验证视频文件是否存在
        if not os.path.exists(request.video_path):
            raise HTTPException(status_code=404, detail="视频文件不存在")

        # 执行多模态分析
        result = await analyze_video(
            request.video_path,
            request.transcription,
            request.screenshot_method,
            request.screenshot_interval,
            request.screenshot_threshold,
            request.use_cache
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/integrate-report")
async def integrate_report(request: MultimodalAnalysisRequest):
    """
    整合报告接口：接收已执行的多模态分析结果，生成详细总结并组合成完整报告
    不再重复执行多模态分析
    """
    try:
        multimodal_result = request.multimodal_result if hasattr(request, 'multimodal_result') and request.multimodal_result else None

        if not multimodal_result:
            raise HTTPException(status_code=400, detail="缺少多模态分析结果")

        # 生成详细总结（包含对话历史作为参考）
        transcription_text = "\n".join([seg['text'] for seg in request.transcription])
        chat_context = ""
        if request.chat_history and len(request.chat_history) > 0:
            # 构建对话上下文摘要
            chat_summary_parts = []
            for msg in request.chat_history[-5:]:  # 只取最近5条对话
                role = msg.get('role', 'user')
                content = msg.get('content', '')[:200]  # 每条限制200字
                chat_summary_parts.append(f"{role}: {content}")
            chat_context = "\n\n对话讨论要点：\n" + "\n".join(chat_summary_parts)

        detailed_summary = ""
        async for chunk in generate_detailed_summary(transcription_text, "", chat_context):
            detailed_summary += chunk

        # 构建综合分析报告
        screenshot_count = multimodal_result.get('screenshot_count', 0)
        ocr_results = multimodal_result.get('ocr_results', [])
        subtitle_results = multimodal_result.get('subtitle_results', [])
        ocr_text_count = len([r for r in ocr_results if r.get('text') and r.get('text').strip()])

        # 安全获取 analysis 字段
        analysis_data = multimodal_result.get('analysis', {})
        if isinstance(analysis_data, dict):
            analysis_summary = analysis_data.get('summary', '')
            mindmap_data = analysis_data.get('mindmap')
        else:
            analysis_summary = str(analysis_data) if analysis_data else ''
            mindmap_data = None

        comprehensive_report = {
            "video_info": multimodal_result.get('video_info', {}),
            "filename": request.video_path.split('/')[-1] if '/' in request.video_path else request.video_path,
            "statistics": {
                "screenshot_count": screenshot_count,
                "ocr_count": ocr_text_count,
                "subtitle_count": len(subtitle_results),
            },
            "multimodal_analysis": multimodal_result,
            "corrected_transcription": multimodal_result.get('corrected_transcription', request.transcription),
            "detailed_summary": detailed_summary,
            "analysis_summary": analysis_summary,
            "mindmap": mindmap_data,
            "ocr_results": ocr_results,
            "subtitle_results": subtitle_results,
            "screenshots": multimodal_result.get('screenshots', []),
            "chat_history": request.chat_history if request.chat_history else [],
        }

        return comprehensive_report

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[integrate_report] 错误: {type(e).__name__}: {str(e)}")
        print(f"[integrate_report] 详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/comprehensive-analysis")
async def comprehensive_analysis(request: MultimodalAnalysisRequest):
    """综合分析接口：整合详细总结、多模态分析和对话交互内容"""
    try:
        # 验证视频文件是否存在
        if not os.path.exists(request.video_path):
            raise HTTPException(status_code=404, detail="视频文件不存在")

        # 1. 执行多模态分析
        multimodal_result = await analyze_video(
            request.video_path,
            request.transcription,
            request.screenshot_method,
            request.screenshot_interval,
            request.screenshot_threshold,
            request.use_cache
        )

        # 2. 生成详细总结（包含对话历史作为参考）
        transcription_text = "\n".join([seg['text'] for seg in request.transcription])
        chat_context = ""
        if request.chat_history and len(request.chat_history) > 0:
            # 构建对话上下文摘要
            chat_summary_parts = []
            for msg in request.chat_history[-5:]:  # 只取最近5条对话
                role = msg.get('role', 'user')
                content = msg.get('content', '')[:200]  # 每条限制200字
                chat_summary_parts.append(f"{role}: {content}")
            chat_context = "\n\n对话讨论要点：\n" + "\n".join(chat_summary_parts)

        detailed_summary = ""
        async for chunk in generate_detailed_summary(transcription_text, "", chat_context):
            detailed_summary += chunk

        # 3. 构建综合分析报告
        screenshot_count = multimodal_result.get('screenshot_count', 0)
        ocr_results = multimodal_result.get('ocr_results', [])
        subtitle_results = multimodal_result.get('subtitle_results', [])
        ocr_text_count = len([r for r in ocr_results if r.get('text') and r.get('text').strip()])

        # 安全获取 analysis 字段
        analysis_data = multimodal_result.get('analysis', {})
        if isinstance(analysis_data, dict):
            analysis_summary = analysis_data.get('summary', '')
            mindmap_data = analysis_data.get('mindmap')
        else:
            analysis_summary = str(analysis_data) if analysis_data else ''
            mindmap_data = None

        comprehensive_report = {
            "video_info": multimodal_result.get('video_info', {}),
            "filename": request.video_path.split('/')[-1] if '/' in request.video_path else request.video_path,
            "statistics": {
                "screenshot_count": screenshot_count,
                "ocr_count": ocr_text_count,
                "subtitle_count": len(subtitle_results),
            },
            "multimodal_analysis": multimodal_result,
            "corrected_transcription": multimodal_result.get('corrected_transcription', request.transcription),
            "detailed_summary": detailed_summary,
            "analysis_summary": analysis_summary,
            "mindmap": mindmap_data,
            "ocr_results": ocr_results,
            "subtitle_results": subtitle_results,
            "screenshots": multimodal_result.get('screenshots', []),
            "chat_history": request.chat_history if request.chat_history else [],
        }

        return comprehensive_report

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[comprehensive_analysis] 错误: {type(e).__name__}: {str(e)}")
        print(f"[comprehensive_analysis] 详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 字幕相关 API ============

@app.get("/api/subtitle-tracks")
async def get_subtitle_tracks(video_path: str = Query(..., description="视频文件路径")):
    """获取视频内置字幕轨道列表"""
    try:
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="视频文件不存在")

        tracks = extract_subtitle_tracks(video_path)
        return {
            "video_path": video_path,
            "subtitle_tracks": tracks,
            "count": len(tracks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/subtitle-file")
async def get_subtitle_file(
    video_path: str = Query(..., description="视频文件路径"),
    track_index: int = Query(0, description="字幕轨道索引"),
    format: str = Query("srt", description="输出格式: srt, ass, vtt")
):
    """提取指定字幕轨道的字幕文件"""
    try:
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="视频文件不存在")

        subtitle_path = extract_subtitle_track(video_path, track_index, format)
        if subtitle_path is None:
            raise HTTPException(status_code=404, detail="字幕轨道提取失败")

        # 生成文件名
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        filename = f"{video_name}_subtitle_{track_index}.{format}"

        return FileResponse(
            path=subtitle_path,
            filename=filename,
            media_type="text/plain",
            background=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-subtitle")
async def generate_subtitle(
    transcription: List[dict] = Body(..., description="转录结果"),
    format: str = Body("srt", description="输出格式: srt, vtt"),
    filename: str = Body("", description="原始文件名（用于生成输出文件名）")
):
    """从转录结果生成字幕文件"""
    try:
        if not transcription:
            raise HTTPException(status_code=400, detail="转录结果为空")

        if format == "vtt":
            subtitle_path = generate_vtt_from_transcription(transcription)
            mime_type = "text/vtt"
        else:
            subtitle_path = generate_srt_from_transcription(transcription)
            mime_type = "application/x-subrip"

        # 生成文件名
        if filename:
            base_name = os.path.splitext(filename)[0]
        else:
            base_name = "transcription"

        output_filename = f"{base_name}.{format}"

        return FileResponse(
            path=subtitle_path,
            filename=output_filename,
            media_type=mime_type,
            background=None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/subtitle-sources")
async def get_subtitle_sources(
    video_path: str = Query(..., description="视频文件路径"),
    has_transcription: bool = Query(False, description="是否有转录结果")
):
    """获取视频所有可用字幕来源"""
    try:
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="视频文件不存在")

        transcription = None  # 暂时不支持传递转录结果
        sources = get_all_subtitle_sources(video_path, transcription)

        return {
            "video_path": video_path,
            **sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 