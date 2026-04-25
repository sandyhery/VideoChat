import { useReducer, useEffect } from 'react';
import api from '../utils/api';

// 初始状态
const initialState = {
  uploadedFiles: [],
  selectedFiles: [],
  currentFile: null,
  mediaUrl: null,
  pageSize: 5,
  currentPage: 1,
  isTranscribing: false,
  abortTranscribing: false,
  loadingStates: {
    mindmap: new Set(),
    summary: new Set(),
    detailedSummary: new Set(),
    multimodal: new Set(),
    comprehensive: new Set(),
  },
};

// Action 类型
const ActionTypes = {
  SET_UPLOADED_FILES: 'SET_UPLOADED_FILES',
  ADD_UPLOADED_FILE: 'ADD_UPLOADED_FILE',
  UPDATE_FILE_STATUS: 'UPDATE_FILE_STATUS',
  UPDATE_FILE_DATA: 'UPDATE_FILE_DATA',
  DELETE_FILE: 'DELETE_FILE',
  SET_SELECTED_FILES: 'SET_SELECTED_FILES',
  SET_CURRENT_FILE: 'SET_CURRENT_FILE',
  SET_MEDIA_URL: 'SET_MEDIA_URL',
  SET_PAGE_SIZE: 'SET_PAGE_SIZE',
  SET_CURRENT_PAGE: 'SET_CURRENT_PAGE',
  SET_IS_TRANSCRIBING: 'SET_IS_TRANSCRIBING',
  SET_ABORT_TRANSCRIBING: 'SET_ABORT_TRANSCRIBING',
  ADD_LOADING: 'ADD_LOADING',
  REMOVE_LOADING: 'REMOVE_LOADING',
  RESET_STATE: 'RESET_STATE',
};

// Reducer
const fileReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.SET_UPLOADED_FILES:
      return {
        ...state,
        uploadedFiles: action.payload,
      };
    case ActionTypes.ADD_UPLOADED_FILE:
      return {
        ...state,
        uploadedFiles: [...state.uploadedFiles, action.payload],
      };
    case ActionTypes.UPDATE_FILE_STATUS:
      return {
        ...state,
        uploadedFiles: state.uploadedFiles.map(file =>
          file.id === action.payload.fileId
            ? { ...file, status: action.payload.status }
            : file
        ),
        currentFile: state.currentFile?.id === action.payload.fileId
          ? { ...state.currentFile, status: action.payload.status }
          : state.currentFile,
      };
    case ActionTypes.UPDATE_FILE_DATA:
      return {
        ...state,
        uploadedFiles: state.uploadedFiles.map(file =>
          file.id === action.payload.fileId
            ? { ...file, ...action.payload.data }
            : file
        ),
        currentFile: state.currentFile?.id === action.payload.fileId
          ? { ...state.currentFile, ...action.payload.data }
          : state.currentFile,
      };
    case ActionTypes.DELETE_FILE:
      const newFiles = state.uploadedFiles.filter(file => file.id !== action.payload);
      return {
        ...state,
        uploadedFiles: newFiles,
        selectedFiles: state.selectedFiles.filter(id => id !== action.payload),
        currentFile: state.currentFile?.id === action.payload
          ? newFiles[0] || null
          : state.currentFile,
        mediaUrl: state.currentFile?.id === action.payload
          ? (newFiles[0] ? { url: newFiles[0].url, type: newFiles[0].type } : null)
          : state.mediaUrl,
      };
    case ActionTypes.SET_SELECTED_FILES:
      return {
        ...state,
        selectedFiles: action.payload,
      };
    case ActionTypes.SET_CURRENT_FILE:
      return {
        ...state,
        currentFile: action.payload,
      };
    case ActionTypes.SET_MEDIA_URL:
      return {
        ...state,
        mediaUrl: action.payload,
      };
    case ActionTypes.SET_PAGE_SIZE:
      return {
        ...state,
        pageSize: action.payload,
        currentPage: 1, // 重置为第一页
      };
    case ActionTypes.SET_CURRENT_PAGE:
      return {
        ...state,
        currentPage: action.payload,
      };
    case ActionTypes.SET_IS_TRANSCRIBING:
      return {
        ...state,
        isTranscribing: action.payload,
      };
    case ActionTypes.SET_ABORT_TRANSCRIBING:
      return {
        ...state,
        abortTranscribing: action.payload,
      };
    case ActionTypes.ADD_LOADING:
      return {
        ...state,
        loadingStates: {
          ...state.loadingStates,
          [action.payload.type]: new Set([...state.loadingStates[action.payload.type], action.payload.fileId]),
        },
      };
    case ActionTypes.REMOVE_LOADING:
      return {
        ...state,
        loadingStates: {
          ...state.loadingStates,
          [action.payload.type]: new Set([...state.loadingStates[action.payload.type]].filter(id => id !== action.payload.fileId)),
        },
      };
    case ActionTypes.RESET_STATE:
      return initialState;
    default:
      return state;
  }
};

const useFileManager = () => {
  const [state, dispatch] = useReducer(fileReducer, initialState);

  // 从本地存储加载数据
  useEffect(() => {
    const savedData = localStorage.getItem('videochat_data');
    if (savedData) {
      try {
        const parsedData = JSON.parse(savedData);
        dispatch({ type: ActionTypes.SET_UPLOADED_FILES, payload: parsedData.uploadedFiles || [] });
        dispatch({ type: ActionTypes.SET_SELECTED_FILES, payload: parsedData.selectedFiles || [] });
        
        if (parsedData.currentFileId) {
          const currentFile = (parsedData.uploadedFiles || []).find(f => f.id === parsedData.currentFileId);
          if (currentFile) {
            dispatch({ type: ActionTypes.SET_CURRENT_FILE, payload: currentFile });
            dispatch({ type: ActionTypes.SET_MEDIA_URL, payload: { url: currentFile.url, type: currentFile.type } });
          }
        }
        
        dispatch({ type: ActionTypes.SET_PAGE_SIZE, payload: parsedData.pageSize || 5 });
        dispatch({ type: ActionTypes.SET_CURRENT_PAGE, payload: parsedData.currentPage || 1 });
      } catch (error) {
        console.error('从本地存储加载数据失败:', error);
      }
    }
  }, []);

  // 保存数据到本地存储
  useEffect(() => {
    try {
      const dataToSave = {
        uploadedFiles: state.uploadedFiles.map(file => ({
          ...file,
          file: null, // 移除file对象，因为它不能被序列化
        })),
        selectedFiles: state.selectedFiles,
        currentFileId: state.currentFile?.id,
        pageSize: state.pageSize,
        currentPage: state.currentPage,
      };
      localStorage.setItem('videochat_data', JSON.stringify(dataToSave));
    } catch (error) {
      console.error('保存数据到本地存储失败:', error);
    }
  }, [state.uploadedFiles, state.selectedFiles, state.currentFile, state.pageSize, state.currentPage]);

  // 处理文件上传
  const handleUpload = (file) => {
    // 检查文件类型 - 支持MIME类型和扩展名
    const fileType = file.type || '';
    const isVideo = fileType.startsWith('video/');
    const isAudio = fileType.startsWith('audio/');

    // 如果MIME类型检测失败，尝试通过扩展名判断
    const videoExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'];
    const audioExtensions = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma'];
    const fileName = file.name.toLowerCase();
    const hasVideoExt = videoExtensions.some(ext => fileName.endsWith(ext));
    const hasAudioExt = audioExtensions.some(ext => fileName.endsWith(ext));

    if (!isVideo && !isAudio && !hasVideoExt && !hasAudioExt) {
      throw new Error('请上传视频或音频文件');
    }

    // 检查文件是否已经存在
    const isExist = state.uploadedFiles.some(f => f.name === file.name);
    if (isExist) {
      throw new Error('文件已存在');
    }

    // 检查文件大小（限制2GB）
    if (file.size > 2 * 1024 * 1024 * 1024) {
      throw new Error('文件大小不能超过2GB');
    }

    // 确定文件类型 - 优先使用MIME类型，否则使用扩展名
    let fileMediaType;
    if (isVideo || hasVideoExt) {
      fileMediaType = 'video';
    } else if (isAudio || hasAudioExt) {
      fileMediaType = 'audio';
    } else {
      fileMediaType = 'video'; // 默认假设为视频
    }

    // 创建文件的URL
    const url = URL.createObjectURL(file);
    const newFile = {
      id: `${file.name}-${Date.now()}`,
      name: file.name,
      type: fileMediaType,
      url: url,
      file: file,
      status: 'waiting',
      transcription: null,
      summary: '',
      detailedSummary: '',
      mindmapData: null,
      multimodalAnalysis: null,
      comprehensiveAnalysis: null,
    };

    dispatch({ type: ActionTypes.ADD_UPLOADED_FILE, payload: newFile });

    // 如果是第一个文件，自动设置为当前预览文件
    if (state.uploadedFiles.length === 0) {
      dispatch({ type: ActionTypes.SET_CURRENT_FILE, payload: newFile });
      dispatch({ type: ActionTypes.SET_MEDIA_URL, payload: { url, type: fileMediaType } });
    }

    return newFile;
  };

  // 处理文件选择
  const handleFileSelect = (fileIds) => {
    dispatch({ type: ActionTypes.SET_SELECTED_FILES, payload: fileIds });
  };

  // 处理文件删除
  const handleFileDelete = (fileId) => {
    dispatch({ type: ActionTypes.DELETE_FILE, payload: fileId });
  };

  // 处理文件预览
  const handleFilePreview = (file) => {
    dispatch({ type: ActionTypes.SET_CURRENT_FILE, payload: file });
    dispatch({ type: ActionTypes.SET_MEDIA_URL, payload: { url: file.url, type: file.type } });
  };

  // 处理批量转录
  const handleBatchTranscribe = async () => {
    if (state.isTranscribing) {
      // 停止转录
      dispatch({ type: ActionTypes.SET_IS_TRANSCRIBING, payload: false });
      dispatch({ type: ActionTypes.SET_ABORT_TRANSCRIBING, payload: true });

      try {
        await api.stopTranscription();

        // 更新正在转录的文件状态为中断
        state.uploadedFiles.forEach(file => {
          if (file.status === 'transcribing') {
            dispatch({ 
              type: ActionTypes.UPDATE_FILE_STATUS, 
              payload: { fileId: file.id, status: 'interrupted' } 
            });
          }
        });

        return '已停止转录';
      } catch (error) {
        console.error('停止转录失败:', error);
        throw error;
      } finally {
        dispatch({ type: ActionTypes.SET_ABORT_TRANSCRIBING, payload: false });
      }
    }

    if (state.selectedFiles.length === 0) {
      throw new Error('请选择需要转录的文件');
    }

    dispatch({ type: ActionTypes.SET_IS_TRANSCRIBING, payload: true });
    dispatch({ type: ActionTypes.SET_ABORT_TRANSCRIBING, payload: false });

    try {
      for (const fileId of state.selectedFiles) {
        // 检查是否已经请求中断
        if (state.abortTranscribing) {
          // 更新正在转录的文件状态为中断
          state.uploadedFiles.forEach(file => {
            if (file.status === 'transcribing') {
              dispatch({ 
                type: ActionTypes.UPDATE_FILE_STATUS, 
                payload: { fileId: file.id, status: 'interrupted' } 
              });
            }
          });
          break;
        }

        const file = state.uploadedFiles.find(f => f.id === fileId);
        if (!file) continue;

        // 只跳过已完成的文件，允许中断状态的文件重新转录
        if (file.status === 'done') {
          continue;
        }

        // 更新文件状态为转录中
        dispatch({ 
          type: ActionTypes.UPDATE_FILE_STATUS, 
          payload: { fileId: file.id, status: 'transcribing' } 
        });

        try {
          // 检查file对象是否存在
          if (!file.file) {
            dispatch({ 
              type: ActionTypes.UPDATE_FILE_STATUS, 
              payload: { fileId: file.id, status: 'waiting' } 
            });
            continue;
          }

          const result = await api.uploadFile(file.file);
          console.log('上传成功:', file.name, result);

          if (state.abortTranscribing) {
            // 更新当前文件状态为中断
            dispatch({
              type: ActionTypes.UPDATE_FILE_STATUS,
              payload: { fileId: file.id, status: 'interrupted' }
            });
            break;
          }

          // 更新文件状态和转录结果
          // 检查转录结果是否有效
          const transcriptionResult = result.transcription;
          const isValidTranscription = transcriptionResult && transcriptionResult.length > 0;

          dispatch({
            type: ActionTypes.UPDATE_FILE_DATA,
            payload: {
              fileId: file.id,
              data: {
                status: isValidTranscription ? 'done' : 'error',
                transcription: transcriptionResult || null
              }
            }
          });

        } catch (error) {
          console.error('转录错误:', file.name, error);
          if (!state.abortTranscribing) {
            dispatch({
              type: ActionTypes.UPDATE_FILE_STATUS,
              payload: { fileId: file.id, status: 'error' }
            });
          }
        }
      }

      return '转录完成';
    } catch (error) {
      console.error('转录失败:', error);
      throw error;
    } finally {
      dispatch({ type: ActionTypes.SET_IS_TRANSCRIBING, payload: false });
      dispatch({ type: ActionTypes.SET_ABORT_TRANSCRIBING, payload: false });
    }
  };

  // 检查是否有转录结果
  const checkTranscription = () => {
    if (!state.currentFile?.transcription || state.currentFile.transcription.length === 0) {
      throw new Error('需等待视频/音频完成转录');
    }
    return true;
  };

  // 处理生成总结
  const handleSummary = async () => {
    checkTranscription();
    if (!state.currentFile) {
      throw new Error('请选择一个文件');
    }

    const fileId = state.currentFile.id;

    if (state.loadingStates.summary.has(fileId)) {
      throw new Error('该文件正在生成总结，请稍候');
    }

    const text = state.currentFile.transcription.map(item => item.text).join('\n');

    try {
      dispatch({ type: ActionTypes.ADD_LOADING, payload: { type: 'summary', fileId } });

      // 初始化内容
      dispatch({ 
        type: ActionTypes.UPDATE_FILE_DATA, 
        payload: { fileId, data: { summary: '' } } 
      });

      const response = await api.getSummary(text);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let summaryText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        summaryText += chunk;

        // 更新文件引用中的内容
        dispatch({ 
          type: ActionTypes.UPDATE_FILE_DATA, 
          payload: { fileId, data: { summary: summaryText } } 
        });
      }

      return summaryText;
    } catch (error) {
      console.error('生成总结失败:', error);
      throw error;
    } finally {
      dispatch({ type: ActionTypes.REMOVE_LOADING, payload: { type: 'summary', fileId } });
    }
  };

  // 处理生成详细总结
  const handleDetailedSummary = async () => {
    checkTranscription();
    if (!state.currentFile) {
      throw new Error('请选择一个文件');
    }

    const fileId = state.currentFile.id;

    if (state.loadingStates.detailedSummary.has(fileId)) {
      throw new Error('该文件正在生成详细总结，请稍候');
    }

    const text = state.currentFile.transcription.map(item => item.text).join('\n');

    try {
      dispatch({ type: ActionTypes.ADD_LOADING, payload: { type: 'detailedSummary', fileId } });

      // 初始化内容
      dispatch({ 
        type: ActionTypes.UPDATE_FILE_DATA, 
        payload: { fileId, data: { detailedSummary: '' } } 
      });

      const response = await api.getDetailedSummary(text);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let summaryText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        summaryText += chunk;

        // 更新文件引用中的内容
        dispatch({ 
          type: ActionTypes.UPDATE_FILE_DATA, 
          payload: { fileId, data: { detailedSummary: summaryText } } 
        });
      }

      return summaryText;
    } catch (error) {
      console.error('生成详细总结失败:', error);
      throw error;
    } finally {
      dispatch({ type: ActionTypes.REMOVE_LOADING, payload: { type: 'detailedSummary', fileId } });
    }
  };

  // 处理生成思维导图
  const handleMindmap = async () => {
    checkTranscription();
    if (!state.currentFile) {
      throw new Error('请选择一个文件');
    }

    const fileId = state.currentFile.id;

    if (state.loadingStates.mindmap.has(fileId)) {
      throw new Error('该文件正在生成思维导图，请稍候');
    }

    const text = state.currentFile.transcription.map(item => item.text).join('\n');

    try {
      dispatch({ type: ActionTypes.ADD_LOADING, payload: { type: 'mindmap', fileId } });

      // 初始化内容
      dispatch({ 
        type: ActionTypes.UPDATE_FILE_DATA, 
        payload: { fileId, data: { mindmapData: null } } 
      });

      const data = await api.generateMindmap(text);

      // 更新文件对象中的思维导图数据
      dispatch({ 
        type: ActionTypes.UPDATE_FILE_DATA, 
        payload: { fileId, data: { mindmapData: data.mindmap } } 
      });

      return data.mindmap;
    } catch (error) {
      console.error('生成思维导图失败:', error);
      throw error;
    } finally {
      dispatch({ type: ActionTypes.REMOVE_LOADING, payload: { type: 'mindmap', fileId } });
    }
  };

  // 处理多模态分析
  const handleMultimodalAnalysis = async () => {
    checkTranscription();
    if (!state.currentFile) {
      throw new Error('请选择一个文件');
    }

    const fileId = state.currentFile.id;

    if (state.loadingStates.multimodal.has(fileId)) {
      throw new Error('该文件正在进行多模态分析，请稍候');
    }

    try {
      dispatch({ type: ActionTypes.ADD_LOADING, payload: { type: 'multimodal', fileId } });

      // 初始化内容
      dispatch({ 
        type: ActionTypes.UPDATE_FILE_DATA, 
        payload: { fileId, data: { multimodalAnalysis: null } } 
      });

      const data = await api.multimodalAnalysis(
        `uploads/${state.currentFile.name}`,
        state.currentFile.transcription,
        'interval',
        5
      );

      // 更新文件对象中的多模态分析数据
      dispatch({ 
        type: ActionTypes.UPDATE_FILE_DATA, 
        payload: { fileId, data: { multimodalAnalysis: data } } 
      });

      return data;
    } catch (error) {
      console.error('多模态分析失败:', error);
      throw error;
    } finally {
      dispatch({ type: ActionTypes.REMOVE_LOADING, payload: { type: 'multimodal', fileId } });
    }
  };

  // 处理综合分析
  const handleComprehensiveAnalysis = async () => {
    checkTranscription();
    if (!state.currentFile) {
      throw new Error('请选择一个文件');
    }

    const fileId = state.currentFile.id;

    if (state.loadingStates.comprehensive.has(fileId)) {
      throw new Error('该文件正在进行综合分析，请稍候');
    }

    try {
      dispatch({ type: ActionTypes.ADD_LOADING, payload: { type: 'comprehensive', fileId } });

      // 初始化内容
      dispatch({ 
        type: ActionTypes.UPDATE_FILE_DATA, 
        payload: { fileId, data: { comprehensiveAnalysis: null } } 
      });

      const data = await api.comprehensiveAnalysis(
        `uploads/${state.currentFile.name}`,
        state.currentFile.transcription,
        'interval',
        5
      );

      // 更新文件对象中的综合分析数据
      dispatch({ 
        type: ActionTypes.UPDATE_FILE_DATA, 
        payload: { fileId, data: { comprehensiveAnalysis: data } } 
      });

      return data;
    } catch (error) {
      console.error('综合分析失败:', error);
      throw error;
    } finally {
      dispatch({ type: ActionTypes.REMOVE_LOADING, payload: { type: 'comprehensive', fileId } });
    }
  };

  // 计算当前页应该显示的文件
  const getPageData = () => {
    const start = (state.currentPage - 1) * state.pageSize;
    const end = start + state.pageSize;
    return state.uploadedFiles.slice(start, end);
  };

  return {
    state,
    dispatch,
    handleUpload,
    handleFileSelect,
    handleFileDelete,
    handleFilePreview,
    handleBatchTranscribe,
    checkTranscription,
    handleSummary,
    handleDetailedSummary,
    handleMindmap,
    handleMultimodalAnalysis,
    handleComprehensiveAnalysis,
    getPageData,
  };
};

export default useFileManager;