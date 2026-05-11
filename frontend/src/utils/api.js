// API 调用封装

const API_BASE_URL = 'http://127.0.0.1:8001/api';

// 通用请求函数
const request = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
  };
  
  const mergedOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...options.headers,
    },
  };
  
  try {
    const response = await fetch(url, mergedOptions);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `请求失败: ${response.status}`);
    }
    
    return response;
  } catch (error) {
    console.error(`API 请求失败: ${url}`, error);
    throw error;
  }
};

// 文件上传
const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const url = `${API_BASE_URL}/upload`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `上传失败: ${response.status}`);
  }

  return response.json();
};

// 获取总结
const getSummary = async (text, filename = "") => {
  return request('/summary', {
    method: 'POST',
    body: JSON.stringify({ text, filename }),
  });
};

// 获取详细总结
const getDetailedSummary = async (text, filename = "") => {
  return request('/detailed-summary', {
    method: 'POST',
    body: JSON.stringify({ text, filename }),
  });
};

// 生成思维导图
const generateMindmap = async (text, filename = "") => {
  const response = await request('/mindmap', {
    method: 'POST',
    body: JSON.stringify({ text, filename }),
  });
  
  return response.json();
};

// 聊天
const chatWithModel = async (messages, context) => {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify({ messages, context }),
  });
};

// 停止转录
const stopTranscription = async () => {
  const response = await request('/stop-transcribe', {
    method: 'POST',
  });
  
  return response.json();
};

// 多模态分析
const multimodalAnalysis = async (videoPath, transcription, screenshotMethod = 'interval', screenshotInterval = 5, screenshotThreshold = 30.0) => {
  const response = await request('/multimodal-analysis', {
    method: 'POST',
    body: JSON.stringify({
      video_path: videoPath,
      transcription,
      screenshot_method: screenshotMethod,
      screenshot_interval: screenshotInterval,
      screenshot_threshold: screenshotThreshold,
    }),
  });
  
  return response.json();
};

// 综合分析
const comprehensiveAnalysis = async (videoPath, transcription, screenshotMethod = 'interval', screenshotInterval = 5, screenshotThreshold = 30.0) => {
  const response = await request('/comprehensive-analysis', {
    method: 'POST',
    body: JSON.stringify({
      video_path: videoPath,
      transcription,
      screenshot_method: screenshotMethod,
      screenshot_interval: screenshotInterval,
      screenshot_threshold: screenshotThreshold,
    }),
  });
  
  return response.json();
};

// 导出转录结果
const exportTranscription = async (format, transcription) => {
  return request(`/export/${format}`, {
    method: 'POST',
    body: JSON.stringify(transcription),
  });
};

// 导出总结
const exportSummary = async (summary) => {
  return request('/export/summary', {
    method: 'POST',
    body: JSON.stringify(summary),
  });
};

// 导出思维导图
const exportMindmap = async (mindmap) => {
  return request('/export/mindmap', {
    method: 'POST',
    body: JSON.stringify({ mindmap }),
  });
};

// 获取视频字幕轨道列表
const getSubtitleTracks = async (videoPath) => {
  const response = await request('/subtitle-tracks', {
    method: 'GET',
  });
  return response.json();
};

// 获取视频字幕文件
const getSubtitleFile = async (videoPath, trackIndex = 0, format = 'srt') => {
  const url = `${API_BASE_URL}/subtitle-file?video_path=${encodeURIComponent(videoPath)}&track_index=${trackIndex}&format=${format}`;
  const response = await fetch(url);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `获取字幕文件失败: ${response.status}`);
  }
  return response;
};

// 从转录生成字幕文件
const generateSubtitle = async (transcription, format = 'srt', filename = '') => {
  const response = await request('/generate-subtitle', {
    method: 'POST',
    body: JSON.stringify({ transcription, format, filename }),
  });
  return response;
};

// 为转录文本添加标点符号和分段
const punctuationTranscription = async (transcription) => {
  const response = await request('/punctuation', {
    method: 'POST',
    body: JSON.stringify({ transcription }),
  });
  return response.json();
};

// 获取所有字幕来源
const getSubtitleSources = async (videoPath, hasTranscription = false) => {
  const url = `${API_BASE_URL}/subtitle-sources?video_path=${encodeURIComponent(videoPath)}&has_transcription=${hasTranscription}`;
  const response = await fetch(url);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `获取字幕来源失败: ${response.status}`);
  }
  return response.json();
};

const api = {
  uploadFile,
  getSummary,
  getDetailedSummary,
  generateMindmap,
  chatWithModel,
  stopTranscription,
  multimodalAnalysis,
  comprehensiveAnalysis,
  exportTranscription,
  exportSummary,
  exportMindmap,
  getSubtitleTracks,
  getSubtitleFile,
  generateSubtitle,
  getSubtitleSources,
};

export default api;