import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Layout, Button, Tabs, Input, message } from 'antd';
import { SendOutlined, CopyOutlined } from '@ant-design/icons';
import Mermaid from 'mermaid';
import './App.css';

// 导入组件
import FileUploader from './components/FileUploader';
import Transcription from './components/Transcription';
import Summary from './components/Summary';
import Mindmap from './components/Mindmap';
import Export from './components/Export';

// 导入钩子和工具
import useFileManager from './hooks/useFileManager';
import api from './utils/api';

const { TextArea } = Input;
const { Content, Sider } = Layout;

function App() {
  // 使用文件管理器钩子
  const {
    state,
    handleUpload,
    handleFileSelect,
    handleFileDelete,
    handleFilePreview,
    handleBatchTranscribe,
    handleSummary,
    handleDetailedSummary,
    handleMindmap,
    handleMultimodalAnalysis,
    handleComprehensiveAnalysis,
    getPageData,
  } = useFileManager();

  // 聊天相关状态
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const abortController = useRef(null);
  const messagesEndRef = useRef(null);

  // 初始化 Mermaid
  useEffect(() => {
    Mermaid.initialize({
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      mindmap: {
        padding: 20,
        curve: 'basis',
        nodeSpacing: 100,
        rankSpacing: 80,
        fontSize: 14,
        wrap: true,
        useMaxWidth: true
      },
      themeVariables: {
        mindmapNode: '#7CB342',
        mindmapNodeBorder: '#558B2F',
        mindmapHover: '#AED581',
        mindmapBorder: '#558B2F',
        primaryColor: '#7CB342',
        lineColor: '#558B2F',
        textColor: '#37474F'
      }
    });
  }, []);

  // 修改 jsMind 的初始化和主题注册
  useEffect(() => {
    // 创建自定义主题
    const customTheme = {
      'background': '#fff',
      'color': '#333',

      'main-color': '#333',
      'main-radius': '4px',
      'main-background-color': '#f0f2f5',
      'main-padding': '10px',
      'main-margin': '0px',
      'main-font-size': '16px',
      'main-font-weight': 'bold',

      'sub-color': '#333',
      'sub-radius': '4px',
      'sub-background-color': '#fff',
      'sub-padding': '8px',
      'sub-margin': '0px',
      'sub-font-size': '14px',
      'sub-font-weight': 'normal',

      'line-width': '2px',
      'line-color': '#558B2F',
    };

    // 注册主题和样式
    if (window.jsMind && window.jsMind.hasOwnProperty('register_theme')) {
      window.jsMind.register_theme('primary', customTheme);
    } else if (window.jsMind && window.jsMind.hasOwnProperty('util') && window.jsMind.util.hasOwnProperty('register_theme')) {
      window.jsMind.util.register_theme('primary', customTheme);
    }

    // 注册节点样式
    const nodeStyles = {
      important: {
        'background-color': '#e6f7ff',
        'border-radius': '4px',
        'padding': '4px 8px',
        'border': '1px solid #91d5ff'
      }
    };

    if (window.jsMind && window.jsMind.hasOwnProperty('register_node_style')) {
      Object.keys(nodeStyles).forEach(style => {
        window.jsMind.register_node_style(style, nodeStyles[style]);
      });
    } else if (window.jsMind && window.jsMind.hasOwnProperty('util') && window.jsMind.util.hasOwnProperty('register_node_style')) {
      Object.keys(nodeStyles).forEach(style => {
        window.jsMind.util.register_node_style(style, nodeStyles[style]);
      });
    }
  }, []);

  // 滚动到消息底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 处理时间点击
  const handleTimeClick = (time) => {
    const mediaRef = document.getElementById('media-player');
    if (mediaRef) {
      mediaRef.currentTime = time;
      mediaRef.play();
    }
  };

  // 处理发送消息
  const handleSendMessage = async () => {
    // 如果正在生成，则停止生成
    if (isGenerating) {
      abortController.current?.abort();
      setIsGenerating(false);
      // 更新最后一条消息为"已停止生成"
      setMessages(prevMessages => {
        const newMessages = [...prevMessages];
        if (newMessages.length > 0) {
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage.role === 'assistant') {
            lastMessage.content += '\n\n*[已停止生成]*';
          }
        }
        return newMessages;
      });
      return;
    }

    // 检查转录和输入
    if (!state.currentFile?.transcription || state.currentFile.transcription.length === 0) {
      message.warning('需等待视频/音频完成转录');
      return;
    }
    if (!inputMessage.trim()) {
      message.warning('请输入消息内容');
      return;
    }

    const newMessage = { role: 'user', content: inputMessage };
    const currentMessages = [...messages, newMessage];
    setMessages(currentMessages);
    setInputMessage('');
    setIsGenerating(true);

    // 创建新的 AbortController
    abortController.current = new AbortController();

    try {
      const response = await api.chatWithModel(
        currentMessages,
        state.currentFile?.transcription.map(item => item.text).join('\n')
      );

      const reader = response.body.getReader();
      let aiResponse = '';

      // 创建 AI 消息占位
      setMessages([...currentMessages, { role: 'assistant', content: '' }]);

      while (true) {
        try {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = new TextDecoder().decode(value);
          aiResponse += chunk;

          setMessages([
            ...currentMessages,
            { role: 'assistant', content: aiResponse }
          ]);
        } catch (error) {
          if (error.name === 'AbortError') {
            // 在被中断时立即退出循环
            break;
          }
          throw error;
        }
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        message.info('已停止生成');
      } else {
        console.error('Error sending message:', error);
        message.error('发送消息失败：' + error.message);
      }
    } finally {
      setIsGenerating(false);
      abortController.current = null;
    }
  };

  // 复制消息
  const handleCopyMessage = (content) => {
    navigator.clipboard.writeText(content)
      .then(() => {
        message.success('复制成功');
      })
      .catch(() => {
        message.error('复制失败');
      });
  };

  // 处理页面大小变化
  const handlePageSizeChange = (size) => {
    // 这里可以添加页面大小变化的处理逻辑
  };

  // 处理页码变化
  const handlePageChange = (page) => {
    // 这里可以添加页码变化的处理逻辑
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout>
        <Sider width={200} style={{ background: '#f0f2f5' }}>
          <div style={{ padding: '16px', fontSize: '18px', fontWeight: 'bold' }}>
            VideoChat
          </div>
        </Sider>
        <Content style={{ padding: '24px' }}>
          <FileUploader
            uploadedFiles={state.uploadedFiles}
            selectedFiles={state.selectedFiles}
            isTranscribing={state.isTranscribing}
            onFileUpload={handleUpload}
            onFileSelect={handleFileSelect}
            onFileDelete={handleFileDelete}
            onFilePreview={handleFilePreview}
            onBatchTranscribe={handleBatchTranscribe}
            pageSize={state.pageSize}
            currentPage={state.currentPage}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
            getPageData={getPageData}
          />

          <div style={{ marginTop: '24px' }}>
            {state.mediaUrl ? (
              <div style={{ marginBottom: '16px' }}>
                {state.mediaUrl.type === 'video' ? (
                  <video
                    id="media-player"
                    width="100%"
                    controls
                  >
                    <source src={state.mediaUrl.url} type="video/mp4" />
                    您的浏览器不支持视频播放。
                  </video>
                ) : (
                  <audio
                    id="media-player"
                    controls
                  >
                    <source src={state.mediaUrl.url} type="audio/mpeg" />
                    您的浏览器不支持音频播放。
                  </audio>
                )}
              </div>
            ) : (
              <div style={{ marginBottom: '16px', padding: '24px', background: '#f0f2f5', textAlign: 'center' }}>
                请上传视频或音频文件
              </div>
            )}

            <Tabs defaultActiveKey="transcription">
              <Tabs.TabPane tab="转录结果" key="transcription">
                <Transcription
                  transcription={state.currentFile?.transcription}
                  onTimeClick={handleTimeClick}
                />
              </Tabs.TabPane>
              <Tabs.TabPane tab="简单总结" key="summary">
                <div style={{ marginBottom: '16px' }}>
                  <Button 
                    type="primary" 
                    onClick={async () => {
                      try {
                        await handleSummary();
                        message.success('生成总结成功');
                      } catch (error) {
                        message.error(error.message);
                      }
                    }}
                    disabled={!state.currentFile?.transcription || state.loadingStates.summary.has(state.currentFile.id)}
                  >
                    生成总结
                  </Button>
                </div>
                <Summary
                  content={state.currentFile?.summary}
                  isLoading={state.currentFile ? state.loadingStates.summary.has(state.currentFile.id) : false}
                />
              </Tabs.TabPane>
              <Tabs.TabPane tab="详细总结" key="detailed-summary">
                <div style={{ marginBottom: '16px' }}>
                  <Button 
                    type="primary" 
                    onClick={async () => {
                      try {
                        await handleDetailedSummary();
                        message.success('生成详细总结成功');
                      } catch (error) {
                        message.error(error.message);
                      }
                    }}
                    disabled={!state.currentFile?.transcription || state.loadingStates.detailedSummary.has(state.currentFile.id)}
                  >
                    生成详细总结
                  </Button>
                </div>
                <Summary
                  content={state.currentFile?.detailedSummary}
                  isLoading={state.currentFile ? state.loadingStates.detailedSummary.has(state.currentFile.id) : false}
                />
              </Tabs.TabPane>
              <Tabs.TabPane tab="思维导图" key="mindmap">
                <div style={{ marginBottom: '16px' }}>
                  <Button 
                    type="primary" 
                    onClick={async () => {
                      try {
                        await handleMindmap();
                        message.success('生成思维导图成功');
                      } catch (error) {
                        message.error(error.message);
                      }
                    }}
                    disabled={!state.currentFile?.transcription || state.loadingStates.mindmap.has(state.currentFile.id)}
                  >
                    生成思维导图
                  </Button>
                </div>
                <Mindmap
                  content={state.currentFile?.mindmapData}
                  isLoading={state.currentFile ? state.loadingStates.mindmap.has(state.currentFile.id) : false}
                  fileId={state.currentFile?.id}
                />
              </Tabs.TabPane>
              <Tabs.TabPane tab="多模态分析" key="multimodal">
                <div style={{ marginBottom: '16px' }}>
                  <Button 
                    type="primary" 
                    onClick={async () => {
                      try {
                        await handleMultimodalAnalysis();
                        message.success('多模态分析完成');
                      } catch (error) {
                        message.error(error.message);
                      }
                    }}
                    disabled={!state.currentFile?.transcription || state.loadingStates.multimodal.has(state.currentFile.id)}
                  >
                    多模态分析
                  </Button>
                </div>
                {state.currentFile?.multimodalAnalysis ? (
                  <div>
                    <h3>视频信息</h3>
                    <p>时长: {state.currentFile.multimodalAnalysis.video_info.duration.toFixed(2)}秒</p>
                    <p>分辨率: {state.currentFile.multimodalAnalysis.video_info.width}x{state.currentFile.multimodalAnalysis.video_info.height}</p>
                    <p>帧率: {state.currentFile.multimodalAnalysis.video_info.fps.toFixed(1)}fps</p>
                    <p>截图数量: {state.currentFile.multimodalAnalysis.screenshot_count}张</p>
                    
                    <h3>分析总结</h3>
                    <p>{state.currentFile.multimodalAnalysis.analysis.summary}</p>
                  </div>
                ) : (
                  <div>暂无多模态分析结果</div>
                )}
              </Tabs.TabPane>
              <Tabs.TabPane tab="综合分析" key="comprehensive">
                <div style={{ marginBottom: '16px' }}>
                  {!state.currentFile?.transcription ? (
                    <div style={{ padding: '12px', background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: '4px', marginBottom: '12px' }}>
                      {!state.currentFile ? '请先选择并上传视频文件' : '请先完成视频转录后再进行综合分析'}
                    </div>
                  ) : null}
                  <Button
                    type="primary"
                    onClick={async () => {
                      try {
                        message.loading('正在进行综合分析（包含详细总结和多模态分析）...', 0);
                        await handleComprehensiveAnalysis();
                        message.success('综合分析完成');
                      } catch (error) {
                        message.error(error.message);
                      } finally {
                        message.destroy();
                      }
                    }}
                    disabled={!state.currentFile?.transcription || state.loadingStates.comprehensive.has(state.currentFile?.id)}
                  >
                    {state.loadingStates.comprehensive.has(state.currentFile?.id) ? '分析中...' : '综合分析'}
                  </Button>
                </div>
                {state.loadingStates.comprehensive.has(state.currentFile?.id) ? (
                  <div style={{ textAlign: 'center', padding: '40px' }}>
                    <div>正在进行综合分析，请稍候...</div>
                    <div style={{ marginTop: '8px', color: '#888' }}>分析过程包括：视频截图、OCR识别、字幕检测、详细总结生成</div>
                  </div>
                ) : state.currentFile?.comprehensiveAnalysis ? (
                  <div style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 300px)' }}>
                    <h3>视频信息统计</h3>
                    <p>时长: {state.currentFile.comprehensiveAnalysis.video_info.duration.toFixed(2)}秒</p>
                    <p>分辨率: {state.currentFile.comprehensiveAnalysis.video_info.width}x{state.currentFile.comprehensiveAnalysis.video_info.height}</p>
                    <p>帧率: {state.currentFile.comprehensiveAnalysis.video_info.fps.toFixed(1)}fps</p>
                    <p>截图数量: {state.currentFile.comprehensiveAnalysis.statistics.screenshot_count}张</p>
                    <p>OCR识别数: {state.currentFile.comprehensiveAnalysis.statistics.ocr_count}张</p>
                    <p>字幕数: {state.currentFile.comprehensiveAnalysis.statistics.subtitle_count}条</p>

                    <h3>详细总结</h3>
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#f5f5f5', padding: '12px', borderRadius: '4px', maxHeight: '400px', overflowY: 'auto' }}>
                      {state.currentFile.comprehensiveAnalysis.detailed_summary}
                    </pre>

                    <h3>多模态分析总结</h3>
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#f5f5f5', padding: '12px', borderRadius: '4px', maxHeight: '400px', overflowY: 'auto' }}>
                      {state.currentFile.comprehensiveAnalysis.analysis_summary}
                    </pre>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#888' }}>
                    点击上方按钮开始综合分析
                  </div>
                )}
              </Tabs.TabPane>
              <Tabs.TabPane tab="聊天" key="chat">
                <div style={{ height: '400px', border: '1px solid #d9d9d9', borderRadius: '4px', padding: '16px', overflowY: 'auto', marginBottom: '16px' }}>
                  {messages.map((message, index) => (
                    <div key={index} style={{ marginBottom: '16px' }}>
                      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                        {message.role === 'user' ? '用户' : 'AI'}
                      </div>
                      <div style={{ padding: '8px', backgroundColor: message.role === 'user' ? '#e6f7ff' : '#f0f0f0', borderRadius: '4px' }}>
                        {message.content}
                      </div>
                      <div style={{ marginTop: '4px', textAlign: 'right' }}>
                        <Button 
                          type="text" 
                          size="small" 
                          icon={<CopyOutlined />}
                          onClick={() => handleCopyMessage(message.content)}
                        >
                          复制
                        </Button>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
                <div style={{ display: 'flex' }}>
                  <TextArea
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="输入您的问题..."
                    style={{ flex: 1, marginRight: '8px' }}
                    onPressEnter={() => handleSendMessage()}
                  />
                  <Button 
                    type="primary" 
                    icon={<SendOutlined />} 
                    onClick={handleSendMessage}
                    loading={isGenerating}
                  >
                    {isGenerating ? '停止' : '发送'}
                  </Button>
                </div>
              </Tabs.TabPane>
            </Tabs>

            <div style={{ marginTop: '24px' }}>
              <Export
                selectedFiles={state.selectedFiles}
                currentFile={state.currentFile}
                uploadedFiles={state.uploadedFiles}
              />
            </div>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;