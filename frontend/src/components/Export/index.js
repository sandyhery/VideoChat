import React from 'react';
import { Button, message, Menu, Dropdown } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import api from '../../utils/api';
import SubtitleManager from '../SubtitleManager';

const Export = ({ selectedFiles, currentFile, uploadedFiles }) => {
  // 导出转录结果
  const handleExportTranscription = async (format) => {
    if (selectedFiles.length === 0) {
      message.warning('请选择需要导出的文件');
      return;
    }

    try {
      message.loading('正在导出选中的文件...', 0);

      for (const fileId of selectedFiles) {
        const file = uploadedFiles.find(f => f.id === fileId);

        if (!file || !file.transcription || file.transcription.length === 0) {
          message.warning(`文件 "${file?.name}" 没有转录结果，已跳过`);
          continue;
        }

        try {
          const response = await api.exportTranscription(format, file.transcription);

          // 获取文件名
          const contentDisposition = response.headers.get('content-disposition');
          let filename = `${file.name.replace(/\.[^/.]+$/, '')}_transcription.${format}`;
          if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
            if (filenameMatch) {
              filename = filenameMatch[1];
            }
          }

          // 下载文件
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);

          message.success(`文件 "${file.name}" 导出成功`);
        } catch (error) {
          message.error(`文件 "${file.name}" 导出失败：${error.message}`);
        }
      }
    } catch (error) {
      console.error('Export failed:', error);
      message.error('导出失败：' + error.message);
    } finally {
      message.destroy();
    }
  };

  // 导出总结
  const handleExportSummary = async (summaryText, type = 'summary') => {
    if (!summaryText) {
      message.warning('没有可导出的内容');
      return;
    }

    try {
      const response = await api.exportSummary(summaryText);

      // 下载文件
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentFile.name.replace(/\.[^/.]+$/, '')}_${type}.md`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      message.success('导出成功');
    } catch (error) {
      console.error('Export failed:', error);
      message.error('导出失败：' + error.message);
    }
  };

  // 导出思维导图
  const handleExportMindmap = async (format = 'json') => {
    if (!currentFile?.mindmapData) {
      message.warning('没有可导出的思维导图数据');
      return;
    }

    try {
      // 解析 mindmapData（可能是 JSON 字符串）
      const parsedMindmap = typeof currentFile.mindmapData === 'string'
        ? JSON.parse(currentFile.mindmapData)
        : currentFile.mindmapData;

      if (format === 'xmind') {
        // 导出为 xmind 格式
        const response = await api.exportMindmap(parsedMindmap);
        const contentDisposition = response.headers.get('content-disposition');
        let filename = `${currentFile.name.replace(/\.[^/.]+$/, '')}_mindmap.xmind`;
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
          if (filenameMatch) {
            filename = filenameMatch[1];
          }
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        message.success('导出思维导图(xmind)成功');
      } else {
        // 导出为 json 格式
        const response = await api.exportMindmap(parsedMindmap);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentFile.name.replace(/\.[^/.]+$/, '')}_mindmap.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        message.success('导出思维导图(json)成功');
      }
    } catch (error) {
      console.error('Export mindmap failed:', error);
      message.error('导出思维导图失败：' + error.message);
    }
  };

  // 导出多模态分析结果
  const handleExportMultimodalAnalysis = () => {
    if (!currentFile?.multimodalAnalysis) {
      message.warning('没有可导出的多模态分析结果');
      return;
    }

    try {
      const analysis = currentFile.multimodalAnalysis;

      let markdownContent = `# 视频多模态分析报告\n\n`;
      markdownContent += `**文件名称**: ${currentFile.name}\n\n`;
      markdownContent += `**导出时间**: ${new Date().toLocaleString()}\n\n`;
      markdownContent += `---\n\n`;

      markdownContent += `## 视频基本信息\n\n`;
      markdownContent += `- **时长**: ${analysis.video_info.duration.toFixed(2)}秒\n`;
      markdownContent += `- **分辨率**: ${analysis.video_info.width}x${analysis.video_info.height}\n`;
      markdownContent += `- **帧率**: ${analysis.video_info.fps.toFixed(1)}fps\n`;
      if (analysis.video_info.codec) {
        markdownContent += `- **编码**: ${analysis.video_info.codec}\n`;
      }
      markdownContent += `- **截图数量**: ${analysis.screenshot_count}张\n\n`;

      markdownContent += `---\n\n`;

      markdownContent += `## 综合分析总结\n\n`;
      markdownContent += `${analysis.analysis.summary}\n\n`;

      if (analysis.analysis.mindmap) {
        markdownContent += `---\n\n`;
        markdownContent += `## 分析思维导图\n\n`;
        markdownContent += `*思维导图数据已包含在导出文件中，可使用思维导图工具查看*\n\n`;

        try {
          const mindmapJson = JSON.stringify(analysis.analysis.mindmap, null, 2);
          markdownContent += `\`\`\`json\n${mindmapJson}\n\`\`\`\n\n`;
        } catch (e) {
          markdownContent += `*思维导图数据格式化失败*\n\n`;
        }
      }

      if (analysis.ocr_results && analysis.ocr_results.length > 0) {
        markdownContent += `---\n\n`;
        markdownContent += `## OCR识别结果\n\n`;

        const ocrTextCount = analysis.ocr_results.filter(r => r.text && r.text.trim()).length;
        if (ocrTextCount > 0) {
          markdownContent += `识别到 ${ocrTextCount} 张含文字的截图\n\n`;

          for (let i = 0; i < analysis.ocr_results.length && i < 10; i++) {
            const ocrResult = analysis.ocr_results[i];
            if (ocrResult.text && ocrResult.text.trim()) {
              const screenshot = analysis.screenshots && analysis.screenshots[i] ?
                ` (第${i+1}张截图, ${analysis.screenshots[i].time.toFixed(1)}秒)` :
                ` (第${i+1}张截图)`;
              markdownContent += `### ${screenshot}\n\n`;
              markdownContent += `${ocrResult.text.trim()}\n\n`;
            }
          }

          if (ocrTextCount > 10) {
            markdownContent += `*还有 ${ocrTextCount - 10} 张截图的识别结果未显示*\n\n`;
          }
        }
      }

      if (analysis.subtitle_results && analysis.subtitle_results.length > 0) {
        markdownContent += `---\n\n`;
        markdownContent += `## 字幕识别结果\n\n`;
        markdownContent += `检测到 ${analysis.subtitle_results.length} 处字幕\n\n`;

        for (let i = 0; i < analysis.subtitle_results.length && i < 20; i++) {
          const subtitle = analysis.subtitle_results[i];
          markdownContent += `**[${subtitle.time.toFixed(1)}秒]**: ${subtitle.text}\n\n`;
        }

        if (analysis.subtitle_results.length > 20) {
          markdownContent += `*还有 ${analysis.subtitle_results.length - 20} 处字幕未显示*\n\n`;
        }
      }

      markdownContent += `---\n\n`;
      markdownContent += `*报告由 VideoChat 多模态分析系统生成*\n`;

      const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentFile.name.replace(/\.[^/.]+$/, '')}_multimodal_analysis.md`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      message.success('导出多模态分析报告成功');
    } catch (error) {
      console.error('Export multimodal analysis failed:', error);
      message.error('导出多模态分析报告失败：' + error.message);
    }
  };

  // 导出综合分析报告
  const handleExportComprehensiveAnalysis = () => {
    if (!currentFile?.comprehensiveAnalysis) {
      message.warning('没有可导出的综合分析报告');
      return;
    }

    try {
      const analysis = currentFile.comprehensiveAnalysis;

      let markdownContent = `# 视频综合分析报告\n\n`;
      markdownContent += `**文件名称**: ${currentFile.name}\n\n`;
      markdownContent += `**导出时间**: ${new Date().toLocaleString()}\n\n`;
      markdownContent += `---\n\n`;

      // 视频信息统计
      markdownContent += `## 视频信息统计\n\n`;
      markdownContent += `- **时长**: ${analysis.video_info.duration.toFixed(2)}秒\n`;
      markdownContent += `- **分辨率**: ${analysis.video_info.width}x${analysis.video_info.height}\n`;
      markdownContent += `- **帧率**: ${analysis.video_info.fps.toFixed(1)}fps\n`;
      if (analysis.video_info.codec) {
        markdownContent += `- **编码**: ${analysis.video_info.codec}\n`;
      }
      markdownContent += `- **截图数量**: ${analysis.statistics.screenshot_count}张\n`;
      markdownContent += `- **OCR识别数**: ${analysis.statistics.ocr_count}张\n`;
      markdownContent += `- **字幕数**: ${analysis.statistics.subtitle_count}条\n\n`;

      markdownContent += `---\n\n`;

      // 详细总结
      markdownContent += `## 详细总结\n\n`;
      markdownContent += `${analysis.detailed_summary}\n\n`;

      markdownContent += `---\n\n`;

      // 多模态分析总结
      markdownContent += `## 多模态分析总结\n\n`;
      markdownContent += `${analysis.analysis_summary}\n\n`;

      // 思维导图
      if (analysis.mindmap) {
        markdownContent += `---\n\n`;
        markdownContent += `## 分析思维导图\n\n`;
        markdownContent += `*思维导图数据已包含在导出文件中，可使用思维导图工具查看*\n\n`;

        try {
          const mindmapJson = JSON.stringify(analysis.mindmap, null, 2);
          markdownContent += `\`\`\`json\n${mindmapJson}\n\`\`\`\n\n`;
        } catch (e) {
          console.error('Mindmap serialization failed:', e);
          markdownContent += `*思维导图数据格式化失败*\n\n`;
        }
      }

      // OCR识别结果
      if (analysis.ocr_results && analysis.ocr_results.length > 0) {
        markdownContent += `---\n\n`;
        markdownContent += `## OCR识别结果\n\n`;

        const ocrTextCount = analysis.ocr_results.filter(r => r.text && r.text.trim()).length;
        if (ocrTextCount > 0) {
          markdownContent += `识别到 ${ocrTextCount} 张含文字的截图\n\n`;

          for (let i = 0; i < analysis.ocr_results.length && i < 10; i++) {
            const ocrResult = analysis.ocr_results[i];
            if (ocrResult.text && ocrResult.text.trim()) {
              const screenshot = analysis.screenshots && analysis.screenshots[i] ?
                ` (第${i+1}张截图, ${analysis.screenshots[i].time.toFixed(1)}秒)` :
                ` (第${i+1}张截图)`;
              markdownContent += `### ${screenshot}\n\n`;
              markdownContent += `${ocrResult.text.trim()}\n\n`;
            }
          }

          if (ocrTextCount > 10) {
            markdownContent += `*还有 ${ocrTextCount - 10} 张截图的识别结果未显示*\n\n`;
          }
        }
      }

      // 字幕识别结果
      if (analysis.subtitle_results && analysis.subtitle_results.length > 0) {
        markdownContent += `---\n\n`;
        markdownContent += `## 字幕识别结果\n\n`;
        markdownContent += `检测到 ${analysis.subtitle_results.length} 处字幕\n\n`;

        for (let i = 0; i < analysis.subtitle_results.length && i < 20; i++) {
          const subtitle = analysis.subtitle_results[i];
          markdownContent += `**[${subtitle.time.toFixed(1)}秒]**: ${subtitle.text}\n\n`;
        }

        if (analysis.subtitle_results.length > 20) {
          markdownContent += `*还有 ${analysis.subtitle_results.length - 20} 处字幕未显示*\n\n`;
        }
      }

      markdownContent += `---\n\n`;
      markdownContent += `*报告由 VideoChat 综合分析系统生成*\n`;

      const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentFile.name.replace(/\.[^/.]+$/, '')}_comprehensive_analysis.md`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      message.success('导出综合分析报告成功');
    } catch (error) {
      console.error('Export comprehensive analysis failed:', error);
      message.error('导出综合分析报告失败：' + error.message);
    }
  };

  // 转录导出菜单项
  const transcriptionMenu = (
    <Menu>
      <Menu.Item onClick={() => handleExportTranscription('txt')}>
        导出为 TXT
      </Menu.Item>
      <Menu.Item onClick={() => handleExportTranscription('srt')}>
        导出为 SRT
      </Menu.Item>
      <Menu.Item onClick={() => handleExportTranscription('vtt')}>
        导出为 VTT
      </Menu.Item>
    </Menu>
  );

  // 总结导出菜单项
  const summaryMenu = (
    <Menu>
      {currentFile?.summary && (
        <Menu.Item onClick={() => handleExportSummary(currentFile.summary, 'summary')}>
          导出简单总结
        </Menu.Item>
      )}
      {currentFile?.detailedSummary && (
        <Menu.Item onClick={() => handleExportSummary(currentFile.detailedSummary, 'detailed_summary')}>
          导出详细总结
        </Menu.Item>
      )}
    </Menu>
  );

  // 思维导图导出菜单项
  const mindmapMenu = (
    <Menu>
      <Menu.Item key="json" onClick={() => handleExportMindmap('json')}>
        导出为 JSON
      </Menu.Item>
      <Menu.Item key="xmind" onClick={() => handleExportMindmap('xmind')}>
        导出为 XMind
      </Menu.Item>
    </Menu>
  );

  return (
    <div className="export">
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Dropdown overlay={transcriptionMenu} disabled={selectedFiles.length === 0}>
          <Button icon={<DownloadOutlined />}>
            导出转录
          </Button>
        </Dropdown>

        <Dropdown overlay={summaryMenu} disabled={!currentFile}>
          <Button icon={<DownloadOutlined />}>
            导出总结
          </Button>
        </Dropdown>

        <Dropdown overlay={mindmapMenu} disabled={!currentFile?.mindmapData}>
          <Button icon={<DownloadOutlined />} disabled={!currentFile?.mindmapData}>
            导出思维导图
          </Button>
        </Dropdown>

        <Button
          icon={<DownloadOutlined />}
          onClick={handleExportMultimodalAnalysis}
          disabled={!currentFile?.multimodalAnalysis}
        >
          导出多模态分析
        </Button>

        <Button
          icon={<DownloadOutlined />}
          onClick={handleExportComprehensiveAnalysis}
          disabled={!currentFile?.comprehensiveAnalysis}
        >
          导出综合分析
        </Button>
      </div>

      {/* 字幕管理面板 */}
      {currentFile && (
        <div style={{ marginTop: 16 }}>
          <SubtitleManager currentFile={currentFile} />
        </div>
      )}
    </div>
  );
};

export default Export;