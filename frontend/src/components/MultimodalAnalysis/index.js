import React from 'react';
import ReactMarkdown from 'react-markdown';

const MultimodalAnalysis = ({ analysis, isLoading }) => {
  if (isLoading) {
    return (
      <div className="multimodal-analysis-loading">
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div style={{ marginBottom: '16px' }}>正在进行多模态分析...</div>
          <div style={{ color: '#888', fontSize: '14px' }}>分析过程包括：视频截图、OCR识别、字幕检测等</div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="multimodal-analysis">
        <div style={{ textAlign: 'center', padding: '40px', color: '#888' }}>
          暂无多模态分析结果
        </div>
      </div>
    );
  }

  return (
    <div className="multimodal-analysis">
      <div className="analysis-section">
        <h3>视频信息</h3>
        <div style={{ marginBottom: '16px' }}>
          <p><strong>时长:</strong> {analysis.video_info?.duration?.toFixed(2) || 0}秒</p>
          <p><strong>分辨率:</strong> {analysis.video_info?.width || 0}x{analysis.video_info?.height || 0}</p>
          <p><strong>帧率:</strong> {analysis.video_info?.fps?.toFixed(1) || 0}fps</p>
          {analysis.screenshot_count !== undefined && (
            <p><strong>截图数量:</strong> {analysis.screenshot_count}张</p>
          )}
        </div>
      </div>

      {analysis.analysis?.summary && (
        <div className="analysis-section">
          <h3>分析总结</h3>
          <div className="markdown-content">
            <ReactMarkdown>{analysis.analysis.summary}</ReactMarkdown>
          </div>
        </div>
      )}

      {analysis.analysis_summary && (
        <div className="analysis-section">
          <h3>综合分析</h3>
          <div className="markdown-content">
            <ReactMarkdown>{analysis.analysis_summary}</ReactMarkdown>
          </div>
        </div>
      )}

      {analysis.detailed_summary && (
        <div className="analysis-section">
          <h3>详细总结</h3>
          <div className="markdown-content">
            <ReactMarkdown>{analysis.detailed_summary}</ReactMarkdown>
          </div>
        </div>
      )}

      {analysis.statistics && (
        <div className="analysis-section">
          <h3>统计信息</h3>
          <div style={{ marginBottom: '16px' }}>
            <p><strong>截图数量:</strong> {analysis.statistics.screenshot_count || 0}张</p>
            <p><strong>OCR识别数:</strong> {analysis.statistics.ocr_count || 0}张</p>
            <p><strong>字幕数:</strong> {analysis.statistics.subtitle_count || 0}条</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default MultimodalAnalysis;