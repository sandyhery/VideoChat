from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
import os
import json
import tempfile
from datetime import datetime
from backend.services.stt_service import transcribe_audio, stop_transcription, is_file_being_transcribed
from backend.services.ai_service import generate_summary, generate_mindmap, chat_with_model, generate_detailed_summary
from backend.services.multimodal_service import analyze_video
from backend.models import ChatMessage, ChatRequest
import asyncio

app = FastAPI()

# 添加静态文件服务
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加一个变量来跟踪转录任务
transcription_task = None

class TextRequest(BaseModel):
    text: str

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    global transcription_task
    try:
        # 验证文件类型
        if not file.content_type.startswith(('video/', 'audio/')):
            raise HTTPException(status_code=400, detail="只支持视频和音频文件")
        
        # 验证文件大小（限制2GB）
        content = await file.read()
        if len(content) > 2 * 1024 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过2GB")
        
        # 保存上传的文件
        file_path = f"uploads/{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # 创建转录任务
        transcription_task = asyncio.create_task(transcribe_audio(file_path))
        try:
            transcription = await transcription_task
            transcription_task = None
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
        async for chunk in generate_summary(request.text):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")

@app.post("/api/mindmap")
async def get_mindmap(request: TextRequest):
    try:
        mindmap_json = await generate_mindmap(request.text)
        return {"mindmap": mindmap_json}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def generate():
        async for chunk in chat_with_model(request.messages, request.context):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")

@app.post("/api/detailed-summary")
async def get_detailed_summary(request: TextRequest):
    async def generate():
        async for chunk in generate_detailed_summary(request.text):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")

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
async def export_mindmap(request: dict = Body(...)):
    try:
        # 获取mindmap数据
        mindmap = request.get("mindmap")
        print(f"Received mindmap data type: {type(mindmap)}")
        
        # 如果是字符串，尝试解析为JSON
        if isinstance(mindmap, str):
            try:
                mindmap = json.loads(mindmap)
                print(f"Parsed mindmap to object type: {type(mindmap)}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse mindmap string: {e}")
                raise HTTPException(status_code=400, detail="Invalid mindmap data format")
        
        if not mindmap:
            raise HTTPException(status_code=400, detail="No mindmap data provided")
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mindmap_{timestamp}.json"
        
        # 创建临时文件
        import tempfile
        temp_file_path = tempfile.mktemp(suffix=".json")
        
        # 写入文件
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(mindmap, f, ensure_ascii=False, indent=2)
        
        # 返回文件
        return FileResponse(
            path=temp_file_path,
            filename=filename,
            media_type="application/json",
            background=None
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error exporting mindmap: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")

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

@app.post("/api/multimodal-analysis")
async def multimodal_analysis(request: MultimodalAnalysisRequest):
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
            request.screenshot_threshold
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/comprehensive-analysis")
async def comprehensive_analysis(request: MultimodalAnalysisRequest):
    """综合分析接口：整合详细总结和多模态分析"""
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
            request.screenshot_threshold
        )

        # 2. 生成详细总结
        transcription_text = "\n".join([seg['text'] for seg in request.transcription])
        detailed_summary = ""
        async for chunk in generate_detailed_summary(transcription_text):
            detailed_summary += chunk

        # 3. 构建综合分析报告
        # 统计信息
        screenshot_count = multimodal_result.get('screenshot_count', 0)
        ocr_results = multimodal_result.get('ocr_results', [])
        subtitle_results = multimodal_result.get('subtitle_results', [])
        ocr_text_count = len([r for r in ocr_results if r.get('text') and r.get('text').strip()])

        comprehensive_report = {
            "video_info": multimodal_result.get('video_info', {}),
            "statistics": {
                "screenshot_count": screenshot_count,
                "ocr_count": ocr_text_count,
                "subtitle_count": len(subtitle_results),
            },
            "multimodal_analysis": multimodal_result,
            "detailed_summary": detailed_summary,
            "analysis_summary": multimodal_result.get('analysis', {}).get('summary', ''),
            "mindmap": multimodal_result.get('analysis', {}).get('mindmap', None),
            "ocr_results": ocr_results,
            "subtitle_results": subtitle_results,
            "screenshots": multimodal_result.get('screenshots', []),
        }

        return comprehensive_report

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))