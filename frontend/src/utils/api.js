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
};

export default api;