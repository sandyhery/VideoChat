import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Layout, Upload, Button, Input, Card, message, Table, Tabs, Pagination } from 'antd';
import { UploadOutlined, SendOutlined, SoundOutlined, SyncOutlined, DownloadOutlined, CopyOutlined, StopOutlined, DeleteOutlined, GithubOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import Mermaid from 'mermaid';
import './App.css';
import jsMind from 'jsmind';
import 'jsmind/style/jsmind.css';

const { TextArea } = Input;

// 修改内容展示组件
const SummaryContent = ({ fileId, content, isLoading }) => {
    const containerId = `summary-content-${fileId}`;

    // 直接使用传入的 content，不再使用本地状态
    return (
        <div key={fileId} id={containerId} className="markdown-content">
            <ReactMarkdown>{content || ''}</ReactMarkdown>
        </div>
    );
};

const DetailedSummaryContent = ({ fileId, content, isLoading }) => {
    const containerId = `detailed-summary-content-${fileId}`;

    return (
        <div key={fileId} id={containerId} className="markdown-content detailed-summary-content">
            <ReactMarkdown>{content || ''}</ReactMarkdown>
        </div>
    );
};

const MindmapContent = ({ fileId, content, isLoading }) => {
    const containerId = `mindmap-container-${fileId}`;

    useEffect(() => {
        if (content && !isLoading) {
            const container = document.getElementById(containerId);
            if (!container) return;

            // 清空容器
            while (container.firstChild) {
                container.removeChild(container.firstChild);
            }

            try {
                const options = {
                    container: containerId,
                    theme: 'primary',
                    editable: false,
                    view: {
                        hmargin: 100,
                        vmargin: 50,
                        line_width: 2,
                        line_color: '#558B2F'
                    },
                    layout: {
                        hspace: 30,
                        vspace: 20,
                        pspace: 13
                    }
                };

                const jm = new jsMind(options);
                const data = typeof content === 'string'
                    ? JSON.parse(content)
                    : content;

                jm.show(data);
            } catch (error) {
                console.error('Failed to render mindmap:', error);
                container.innerHTML = '<div class="mindmap-error">思维导图渲染失败</div>';
            }
        }
    }, [content, isLoading, containerId, fileId]);

    // 如果正在加载，显示加载提示
    if (isLoading) {
        return (
            <div id={containerId} className="mindmap-container">
                <div className="mindmap-loading">
                    <div className="loading-spinner"></div>
                    <p>正在生成思维导图...</p>
                </div>
            </div>
        );
    }

    // 如果有内容，显示思维导图容器
    if (content) {
        return <div key={fileId} id={containerId} className="mindmap-container" />;
    }

    // 如果既不是加载中也没有内容，返回空容器
    return <div id={containerId} className="mindmap-container" />;
};

function App() {
    const [summary, setSummary] = useState('');
    // eslint-disable-next-line no-unused-vars
    const [mindmap, setMindmap] = useState('');
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [mediaUrl, setMediaUrl] = useState(null);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [isMindmapLoading, setIsMindmapLoading] = useState(false);
    const mediaRef = useRef(null);
    const [detailedSummary, setDetailedSummary] = useState('');
    const [isUserScrolling, setIsUserScrolling] = useState(false);
    const messagesEndRef = useRef(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const abortController = useRef(null);
    const [isComposing, setIsComposing] = useState(false);
    const jmInstanceRef = useRef(null);
    const [uploadedFiles, setUploadedFiles] = useState([]);  // 存储上传的文件列表
    const [selectedFiles, setSelectedFiles] = useState([]);  // 存储选中的文件
    const [currentFile, setCurrentFile] = useState(null);    // 当前预览的文件
    const [pageSize, setPageSize] = useState(5); // 默认每页显示5个文件
    const [currentPage, setCurrentPage] = useState(1); // 添加当前页码状态
    const [abortTranscribing, setAbortTranscribing] = useState(false); // 添加停止转录状态
    const [mindmapLoadingFiles, setMindmapLoadingFiles] = useState(new Set());
    const [summaryLoadingFiles, setSummaryLoadingFiles] = useState(new Set());
    const [detailedSummaryLoadingFiles, setDetailedSummaryLoadingFiles] = useState(new Set());
    const [multimodalLoadingFiles, setMultimodalLoadingFiles] = useState(new Set());
    const [comprehensiveLoadingFiles, setComprehensiveLoadingFiles] = useState(new Set());

    // 打印 uploadedFiles 的变化
    useEffect(() => {
        console.log('Uploaded Files:', uploadedFiles);
    }, [uploadedFiles]);

    // 初始化 Mermaid
    React.useEffect(() => {
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

    const handleUpload = async (file) => {
        // 检查文件类型
        const isVideo = file.type.startsWith('video/');
        const isAudio = file.type.startsWith('audio/');

        if (!isVideo && !isAudio) {
            message.error('请上传视频或音频文件');
            return false;
        }

        // 检查文件是否已经存在
        const isExist = uploadedFiles.some(f => f.name === file.name);
        if (isExist) {
            message.warning('文件已存在');
            return false;
        }

        // 创建文件的URL
        const url = URL.createObjectURL(file);
        const newFile = {
            id: `${file.name}-${Date.now()}`,
            name: file.name,
            type: isVideo ? 'video' : 'audio',
            url: url,
            file: file,
            status: 'waiting',
            transcription: null,
            summary: '',
            detailedSummary: '',
            mindmapData: null,
        };

        setUploadedFiles(prev => [...prev, newFile]);

        // 如果是第一个文件，动设置为当前预览文件
        if (uploadedFiles.length === 0) {
            setCurrentFile(newFile);
            setMediaUrl({ url, type: isVideo ? 'video' : 'audio' });
        }

        return false; // 阻止自动上传
    };

    // 处理文件选择
    const handleFileSelect = (fileIds) => {
        setSelectedFiles(fileIds);
    };

    // 添加分页配置
    const paginationConfig = {
        current: currentPage, // 当前页码
        pageSize: pageSize,
        showSizeChanger: true,
        pageSizeOptions: ['5', '10', '20', '50'],
        showTotal: (total) => `共 ${total} 个文件`,
        onChange: (page, size) => {
            setCurrentPage(page); // 更新当前页码
            setPageSize(size); // 更新每页显示数量
        },
        onShowSizeChange: (current, size) => {
            setCurrentPage(1); // 切换每页显示数量时重置为第一页
            setPageSize(size);
        },
    };

    // 计算当前页应该显示的文件
    const getPageData = () => {
        const start = (currentPage - 1) * pageSize;
        const end = start + pageSize;
        return uploadedFiles.slice(start, end);
    };

    // 文件列表列定
    const fileColumns = [
        {
            title: '文件名',
            dataIndex: 'name',
            key: 'name',
            width: '70%',
        },
        {
            title: '类型',
            dataIndex: 'type',
            key: 'type',
            render: (type) => type === 'video' ? '视频' : '音频',
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            render: (status) => {
                switch (status) {
                    case 'waiting': return '等待转录';
                    case 'transcribing': return <><SyncOutlined spin /> 转录中</>;
                    case 'done': return <span style={{ color: '#52c41a' }}>已完成</span>;
                    case 'error': return <span style={{ color: '#ff4d4f' }}>失败</span>;
                    case 'interrupted': return <span style={{ color: '#faad14' }}>转录中断</span>;
                    default: return status;
                }
            },
        },
        {
            title: '操作',
            key: 'action',
            render: (_, record) => (
                <Button
                    type="text"
                    danger
                    onClick={(e) => {
                        e.stopPropagation();
                        handleFileDelete(record.id);
                    }}
                    icon={<DeleteOutlined />}
                    disabled={record.status === 'transcribing'}
                >
                    删除
                </Button>
            ),
        },
    ];

    // 处理文件删除
    const handleFileDelete = (fileId) => {
        setUploadedFiles(prev => prev.filter(file => file.id !== fileId));
        setSelectedFiles(prev => prev.filter(id => id !== fileId));

        if (currentFile?.id === fileId) {
            const remainingFiles = uploadedFiles.filter(file => file.id !== fileId);
            const nextFile = remainingFiles[0];
            if (nextFile) {
                setCurrentFile(nextFile);
                setMediaUrl({ url: nextFile.url, type: nextFile.type });
            } else {
                setCurrentFile(null);
                setMediaUrl(null);
            }
        }
    };

    // 修改文件预览函数
    const handleFilePreview = (file) => {
        const currentFileRef = uploadedFiles.find(f => f.id === file.id);
        setCurrentFile(currentFileRef);
        setMediaUrl({ url: file.url, type: file.type });
    };

    // 修改批量转录函数
    const handleBatchTranscribe = async () => {
        if (isTranscribing) {
            setIsTranscribing(false);  // 立即更新状态
            setAbortTranscribing(true);

            try {
                const response = await fetch('http://localhost:8001/api/stop-transcribe', {
                    method: 'POST',
                });

                if (!response.ok) {
                    throw new Error('停止转录失败');
                }

                // 只将正在转录的文件状态改为中断
                setUploadedFiles(prev => prev.map(f =>
                    f.status === 'transcribing'
                        ? { ...f, status: 'interrupted' }
                        : f
                ));

                message.success('已停止转录');
            } catch (error) {
                console.error('Failed to stop transcription:', error);
                message.error('停止转录失败：' + error.message);
            } finally {
                setAbortTranscribing(false);
            }
            return;
        }

        if (selectedFiles.length === 0) {
            message.warning('请选需要转录的文件');
            return;
        }

        setIsTranscribing(true);
        setAbortTranscribing(false);
        message.loading('开始转录选中的文件...', 0);

        try {
            for (const fileId of selectedFiles) {
                // 检查是否已经请求中断
                if (abortTranscribing) {
                    // 只将当前在转的文件状态改为中断
                    setUploadedFiles(prev => prev.map(f =>
                        f.status === 'transcribing'
                            ? { ...f, status: 'interrupted' }
                            : f
                    ));
                    break;
                }

                const file = uploadedFiles.find(f => f.id === fileId);
                if (!file) continue;

                // 修改这里：只跳过已完成的文件，允许中断状态的文件重新转录
                if (file.status === 'done') {
                    message.info(`文件 "${file.name}" 已经转录完成，跳过此文件。`);
                    continue;
                }

                // 更新文件状态为转录中
                setUploadedFiles(prev => prev.map(f =>
                    f.id === fileId ? { ...f, status: 'transcribing' } : f
                ));

                try {
                    const formData = new FormData();
                    formData.append('file', file.file, file.name);

                    const response = await fetch('http://localhost:8001/api/upload', {
                        method: 'POST',
                        body: formData,
                    });

                    const data = await response.json();

                    if (response.status === 499) {
                        // 处理转录中断的情况，只更新当前文件状态
                        setUploadedFiles(prev => prev.map(f =>
                            f.id === fileId
                                ? { ...f, status: 'interrupted' }
                                : f
                        ));
                        break; // 中断后续文件的转录
                    }

                    if (!response.ok) {
                        throw new Error(`转录失败: ${file.name}`);
                    }

                    if (!abortTranscribing) {  // 添加检查，确保没有中断请求
                        setUploadedFiles(prev => {
                            const newFiles = prev.map(f =>
                                f.id === fileId ? {
                                    ...f,
                                    status: 'done',
                                    transcription: data.transcription
                                } : f
                            );
                            return newFiles;
                        });

                        if (currentFile?.id === fileId) {
                            setCurrentFile(prev => ({
                                ...prev,
                                status: 'done',
                                transcription: data.transcription
                            }));
                        }
                    }
                } catch (error) {
                    if (!abortTranscribing) {  // 添加检查，确保没有中断请求
                        setUploadedFiles(prev => prev.map(f =>
                            f.id === fileId ? { ...f, status: 'error' } : f
                        ));
                        message.error(`文件 "${file.name}" 转录失败：${error.message}`);
                    }
                }
            }
        } catch (error) {
            console.error('Transcription failed:', error);
            message.error('转录失败：' + error.message);
        } finally {
            setIsTranscribing(false);
            setAbortTranscribing(false);
            message.destroy();
        }
    };

    // 检查是否有转录结果的函数
    const checkTranscription = () => {
        if (!currentFile?.transcription || currentFile.transcription.length === 0) {
            message.warning('需等待视频/音频完成转录');
            return false;
        }
        return true;
    };

    // 修改简单总结函数
    const handleSummary = async () => {
        if (!checkTranscription()) return;
        if (!currentFile) return;

        const fileId = currentFile.id;

        if (summaryLoadingFiles.has(fileId)) {
            message.warning('该文件正在生成总结，请稍候');
            return;
        }

        const text = currentFile.transcription.map(item => item.text).join('\n');
        try {
            setSummaryLoadingFiles(prev => new Set([...prev, fileId]));

            // 找到文件在 uploadedFiles 中的引用
            const fileRef = uploadedFiles.find(f => f.id === fileId);
            if (!fileRef) return;

            // 初始化内容
            fileRef.summary = '';
            // 强制更新 uploadedFiles 以触发重渲染
            setUploadedFiles([...uploadedFiles]);

            const response = await fetch('http://localhost:8001/api/summary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text }),
            });

            if (!response.ok) {
                throw new Error('生成总结失败');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let summaryText = '';
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // 处理每一行
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.choices && parsed.choices[0].delta.content) {
                                summaryText += parsed.choices[0].delta.content;
                            } else if (parsed.choices && parsed.choices[0].message.content) {
                                summaryText += parsed.choices[0].message.content;
                            }
                        } catch (e) {
                            // 忽略解析错误
                        }
                    }
                }

                // 直接更新文件引用中的内容
                fileRef.summary = summaryText;
                // 强制更新 uploadedFiles 以触发重渲染
                setUploadedFiles([...uploadedFiles]);
                // 同时更新currentFile的内容
                if (currentFile.id === fileId) {
                    setCurrentFile(prev => ({ ...prev, summary: summaryText }));
                }
            }

        } catch (error) {
            console.error('Summary generation failed:', error);
            message.error('生成总结失败：' + error.message);
        } finally {
            setSummaryLoadingFiles(prev => {
                const newSet = new Set(prev);
                newSet.delete(fileId);
                return newSet;
            });
        }
    };

    // 修改生成思维导图的函数
    const handleMindmap = async () => {
        if (!checkTranscription()) return;
        if (!currentFile) return;

        const fileId = currentFile.id; // 保存当前文件ID

        // 检查当前文件是否正在生成思维导图
        if (mindmapLoadingFiles.has(fileId)) {
            message.warning('该文件正在生成思维导图，请稍候');
            return;
        }

        const text = currentFile.transcription.map(item => item.text).join('\n');
        try {
            // 将当前文件添加到正在生成的集合中
            setMindmapLoadingFiles(prev => new Set([...prev, fileId]));

            // 找到文件在 uploadedFiles 中的引用
            const fileRef = uploadedFiles.find(f => f.id === fileId);
            if (!fileRef) return;

            // 初始化内容
            fileRef.mindmapData = null;
            // 强制更新 uploadedFiles 以触发重渲染
            setUploadedFiles([...uploadedFiles]);

            const response = await fetch('http://localhost:8001/api/mindmap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text }),
            });

            if (!response.ok) {
                throw new Error('生成思维导图失败');
            }

            const data = await response.json();

            // 更新文件对象中的思维导图数据
            fileRef.mindmapData = data.mindmap;
            // 强制更新 uploadedFiles 以触发重渲染
            setUploadedFiles([...uploadedFiles]);
            // 同时更新currentFile的内容
            if (currentFile.id === fileId) {
                setCurrentFile(prev => ({ ...prev, mindmapData: data.mindmap }));
            }

        } catch (error) {
            console.error('Failed to generate mindmap:', error);
            message.error('生成思维导图失败：' + error.message);
        } finally {
            // 从正在生成的集合中移除当前文件
            setMindmapLoadingFiles(prev => {
                const newSet = new Set(prev);
                newSet.delete(fileId);
                return newSet;
            });
        }
    };

    // 在组件卸载时清理
    useEffect(() => {
        return () => {
            if (jmInstanceRef.current) {
                jmInstanceRef.current = null;
            }
        };
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

        // 册主和样式
        if (jsMind.hasOwnProperty('register_theme')) {
            jsMind.register_theme('primary', customTheme);
        } else if (jsMind.hasOwnProperty('util') && jsMind.util.hasOwnProperty('register_theme')) {
            jsMind.util.register_theme('primary', customTheme);
        }

        // 注册节点式
        const nodeStyles = {
            important: {
                'background-color': '#e6f7ff',
                'border-radius': '4px',
                'padding': '4px 8px',
                'border': '1px solid #91d5ff'
            }
        };

        if (jsMind.hasOwnProperty('register_node_style')) {
            Object.keys(nodeStyles).forEach(style => {
                jsMind.register_node_style(style, nodeStyles[style]);
            });
        } else if (jsMind.hasOwnProperty('util') && jsMind.util.hasOwnProperty('register_node_style')) {
            Object.keys(nodeStyles).forEach(style => {
                jsMind.util.register_node_style(style, nodeStyles[style]);
            });
        }
    }, []);

    // 修改发送消息函数
    const handleSendMessage = async () => {
        // 如果正在生成，则停止生成
        if (isGenerating) {
            abortController.current?.abort();
            setIsGenerating(false);
            // 更新最后一条息为"已停止生成"
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
        if (!checkTranscription()) return;
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
            const response = await fetch('http://localhost:8001/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: currentMessages,
                    context: currentFile?.transcription.map(item => item.text).join('\n'),
                }),
                signal: abortController.current.signal
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const reader = response.body.getReader();
            let aiResponse = '';

            // 创建 AI 息占位
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

    // 添加时点转函数
    const handleTimeClick = (time) => {
        if (mediaRef.current) {
            mediaRef.current.currentTime = time;
            mediaRef.current.play();
        }
    };

    // 添加时间格式化函数
    const formatTime = (seconds) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        if (hours > 0) {
            return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    // 定义表格列
    const transcriptionColumns = [
        {
            title: '时间点',
            dataIndex: 'time',
            key: 'time',
            width: '30%',
            render: (_, record) => (
                <Button
                    type="link"
                    onClick={() => handleTimeClick(record.start)}
                    style={{ padding: 0 }}
                >
                    [{formatTime(record.start)} - {formatTime(record.end)}]
                </Button>
            ),
        },
        {
            title: '内容',
            dataIndex: 'text',
            key: 'text',
        },
    ];

    // 修改导出函数
    const handleExport = async (format) => {
        // 查是否有选中的文件
        if (selectedFiles.length === 0) {
            message.warning('请选择需要导出的文件');
            return;
        }

        try {
            // 显示导进度
            message.loading('正在导出选中的文件...', 0);

            // 遍历选中的文件
            for (const fileId of selectedFiles) {
                const file = uploadedFiles.find(f => f.id === fileId);

                // 检查文件是否有转录结果
                if (!file || !file.transcription || file.transcription.length === 0) {
                    message.warning(`文件 "${file?.name}" 没有转录结果，已跳过`);
                    continue;
                }

                try {
                    const response = await fetch(`http://localhost:8001/api/export/${format}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(file.transcription),
                    });

                    if (!response.ok) {
                        throw new Error(`导出失败: ${file.name}`);
                    }

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
            message.destroy(); // 清除loading息
        }
    };

    // 修改详细总结函数
    const handleDetailedSummary = async () => {
        if (!checkTranscription()) return;
        if (!currentFile) return;

        const fileId = currentFile.id;

        if (detailedSummaryLoadingFiles.has(fileId)) {
            message.warning('该文件正在生成详细总结，请稍候');
            return;
        }

        const text = currentFile.transcription.map(item => item.text).join('\n');
        try {
            setDetailedSummaryLoadingFiles(prev => new Set([...prev, fileId]));

            // 找到文件在 uploadedFiles 中的引用
            const fileRef = uploadedFiles.find(f => f.id === fileId);
            if (!fileRef) return;

            // 初始化内容
            fileRef.detailedSummary = '';
            // 强制更新 uploadedFiles 以触发重渲染
            setUploadedFiles([...uploadedFiles]);

            const response = await fetch('http://localhost:8001/api/detailed-summary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text }),
            });

            if (!response.ok) {
                throw new Error('生成详细总结失败');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let summaryText = '';
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // 处理每一行
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // 保留不完整的行

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.choices && parsed.choices[0]) {
                                if (parsed.choices[0].delta && parsed.choices[0].delta.content) {
                                    summaryText += parsed.choices[0].delta.content;
                                } else if (parsed.choices[0].message && parsed.choices[0].message.content) {
                                    summaryText += parsed.choices[0].message.content;
                                }
                            }
                        } catch (e) {
                            // 忽略解析错误，可能是不完整的JSON
                        }
                    }
                }

                // 直接更新文件引用中的内容
                fileRef.detailedSummary = summaryText;
                // 强制更新 uploadedFiles 以触发重渲染
                setUploadedFiles([...uploadedFiles]);
                // 同时更新currentFile的内容
                if (currentFile.id === fileId) {
                    setCurrentFile(prev => ({ ...prev, detailedSummary: summaryText }));
                }
            }

        } catch (error) {
            console.error('Detailed summary generation failed:', error);
            message.error('生成详细总结失败：' + error.message);
        } finally {
            setDetailedSummaryLoadingFiles(prev => {
                const newSet = new Set(prev);
                newSet.delete(fileId);
                return newSet;
            });
        }
    };

    // 添加导出总结函数
    const handleExportSummary = async (summaryText, type = 'summary') => {
        if (!summaryText) {
            message.warning('没有可导出的内容');
            return;
        }

        try {
            const response = await fetch(`http://localhost:8001/api/export/summary`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(summaryText),
            });

            if (!response.ok) {
                throw new Error('导出失败');
            }

            // 下载文件
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${type}_${new Date().toISOString().slice(0, 10)}.md`;
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

    // 添加多模态分析函数
    const handleMultimodalAnalysis = async () => {
        if (!currentFile?.transcription || currentFile.transcription.length === 0) {
            message.warning('需等待视频/音频完成转录');
            return;
        }
        if (!currentFile) return;

        const fileId = currentFile.id;

        if (multimodalLoadingFiles.has(fileId)) {
            message.warning('该文件正在进行多模态分析，请稍候');
            return;
        }

        try {
            setMultimodalLoadingFiles(prev => new Set([...prev, fileId]));

            // 更新文件状态
            setUploadedFiles(prev => prev.map(f =>
                f.id === fileId ? { ...f, multimodalAnalysis: null } : f
            ));

            const response = await fetch('http://localhost:8001/api/multimodal-analysis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_path: `uploads/${currentFile.name}`,
                    transcription: currentFile.transcription,
                    screenshot_method: 'interval',
                    screenshot_interval: 5
                }),
            });

            if (!response.ok) {
                throw new Error('多模态分析失败');
            }

            const data = await response.json();

            // 更新文件对象中的多模态分析数据
            setUploadedFiles(prev => prev.map(f =>
                f.id === fileId ? { ...f, multimodalAnalysis: data } : f
            ));
            if (currentFile.id === fileId) {
                setCurrentFile(prev => ({ ...prev, multimodalAnalysis: data }));
            }

            message.success('多模态分析完成');

        } catch (error) {
            console.error('Multimodal analysis failed:', error);
            message.error('多模态分析失败：' + error.message);
        } finally {
            setMultimodalLoadingFiles(prev => {
                const newSet = new Set(prev);
                newSet.delete(fileId);
                return newSet;
            });
        }
    };

    // 添加综合分析函数
    const handleComprehensiveAnalysis = async () => {
        if (!currentFile?.transcription || currentFile.transcription.length === 0) {
            message.warning('需等待视频/音频完成转录');
            return;
        }
        if (!currentFile) return;

        const fileId = currentFile.id;

        if (comprehensiveLoadingFiles.has(fileId)) {
            message.warning('该文件正在进行综合分析，请稍候');
            return;
        }

        try {
            setComprehensiveLoadingFiles(prev => new Set([...prev, fileId]));

            // 更新文件状态
            setUploadedFiles(prev => prev.map(f =>
                f.id === fileId ? { ...f, comprehensiveAnalysis: null } : f
            ));

            message.loading('正在进行综合分析（包含详细总结和多模态分析）...', 0);

            const response = await fetch('http://localhost:8001/api/comprehensive-analysis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_path: `uploads/${currentFile.name}`,
                    transcription: currentFile.transcription,
                    screenshot_method: 'interval',
                    screenshot_interval: 5
                }),
            });

            message.destroy();

            if (!response.ok) {
                throw new Error('综合分析失败');
            }

            const data = await response.json();

            // 更新文件对象中的综合分析数据
            setUploadedFiles(prev => prev.map(f =>
                f.id === fileId ? { ...f, comprehensiveAnalysis: data } : f
            ));
            if (currentFile.id === fileId) {
                setCurrentFile(prev => ({ ...prev, comprehensiveAnalysis: data }));
            }

            message.success('综合分析完成');

        } catch (error) {
            message.destroy();
            console.error('Comprehensive analysis failed:', error);
            message.error('综合分析失败：' + error.message);
        } finally {
            setComprehensiveLoadingFiles(prev => {
                const newSet = new Set(prev);
                newSet.delete(fileId);
                return newSet;
            });
        }
    };

    // 导出综合分析报告
    const handleExportComprehensiveAnalysis = () => {
        if (!currentFile?.comprehensiveAnalysis) {
            message.warning('没有可导出的综合分析报告');
            return;
        }

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
                const mindmapJson = typeof analysis.mindmap === 'string'
                    ? analysis.mindmap
                    : JSON.stringify(analysis.mindmap, null, 2);
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
                        const screenshot = analysis.screenshots && analysis.screenshots[i]
                            ? ` (第${i+1}张截图, ${analysis.screenshots[i].time.toFixed(1)}秒)`
                            : ` (第${i+1}张截图)`;
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

        // 下载文件
        const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentFile.name.replace(/\.[^/.]+$/, '')}_综合分析报告.md`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        message.success('导出成功');
    };

    // 添加复制功能
    const handleCopyMessage = (content) => {
        navigator.clipboard.writeText(content)
            .then(() => {
                message.success('复制成功');
            })
            .catch(() => {
                message.error('复制失败');
            });
    };

    // 添加滚动处理函数
    const handleScroll = (e) => {
        const element = e.target;
        const isScrolledToBottom = Math.abs(element.scrollHeight - element.scrollTop - element.clientHeight) < 10;
        setIsUserScrolling(!isScrolledToBottom);
    };

    // 添加滚动到底部的函数
    const scrollToBottom = useCallback(() => {
        if (messagesEndRef.current && !isUserScrolling) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [isUserScrolling]);

    // 监听消息变化，自动滚动
    useEffect(() => {
        scrollToBottom();
    }, [messages, scrollToBottom]);

    // 添加全部删除的处理函数
    const handleDeleteAll = () => {
        if (selectedFiles.length === 0) {
            message.warning('请选择需要删除的文件');
            return;
        }

        // 删除选中的文件
        setUploadedFiles(prev => prev.filter(file => !selectedFiles.includes(file.id)));
        setSelectedFiles([]); // 清空选中状态

        // 如果当前预览的文件被删除，则切换到第一个可用文件
        if (currentFile && selectedFiles.includes(currentFile.id)) {
            const remainingFiles = uploadedFiles.filter(file => !selectedFiles.includes(file.id));
            const nextFile = remainingFiles[0];
            if (nextFile) {
                setCurrentFile(nextFile);
                setMediaUrl({ url: nextFile.url, type: nextFile.type });
            } else {
                setCurrentFile(null);
                setMediaUrl(null);
            }
        }

        message.success('已删除选中的文件');
    };

    // 添加一个函数来计算选中的已转录文件数量
    const getSelectedTranscribedFilesCount = () => {
        return uploadedFiles.filter(file =>
            selectedFiles.includes(file.id) && file.status === 'done'
        ).length;
    };

    // 修改标签页内容
    const tabItems = [
        {
            key: '1',
            label: '转录结果',
            children: (
                <div className="tab-content">
                    <div className="export-section">
                        <div className="selection-tip">
                            {selectedFiles.length > 0 && (
                                <span>已选择 {getSelectedTranscribedFilesCount()} 个转录文件</span>
                            )}
                        </div>
                        <div className="export-buttons">
                            <Button.Group size="small">
                                <Button
                                    onClick={() => handleExport('vtt')}
                                    icon={<DownloadOutlined />}
                                    disabled={!currentFile?.transcription}
                                >
                                    VTT
                                </Button>
                                <Button
                                    onClick={() => handleExport('srt')}
                                    icon={<DownloadOutlined />}
                                    disabled={!currentFile?.transcription}
                                >
                                    SRT
                                </Button>
                                <Button
                                    onClick={() => handleExport('txt')}
                                    icon={<DownloadOutlined />}
                                    disabled={!currentFile?.transcription}
                                >
                                    TXT
                                </Button>
                            </Button.Group>
                        </div>
                    </div>
                    {!currentFile ? (
                        <div className="empty-state">
                            <p>请在左侧选择要查看转录结果的文件</p>
                        </div>
                    ) : (
                        <>
                            {currentFile && (
                                <div className="current-file-tip">
                                    <span>当前文件：{currentFile.name}</span>
                                </div>
                            )}
                            {!currentFile.transcription ? (
                                <div className="empty-state">
                                    <p>当前文件尚未完成转录</p>
                                </div>
                            ) : (
                                <Table
                                    dataSource={currentFile.transcription.map((item, index) => ({
                                        ...item,
                                        key: index,
                                    }))}
                                    columns={transcriptionColumns}
                                    pagination={false}
                                    size="small"
                                    className="transcription-table full-height"
                                />
                            )}
                        </>
                    )}
                </div>
            ),
        },
        {
            key: '2',
            label: '简单总结',
            children: (
                <div className="tab-content">
                    {currentFile && (
                        <div className="current-file-tip">
                            <span>当前文件：{currentFile.name}</span>
                        </div>
                    )}
                    <div className="button-group">
                        <Button
                            onClick={handleSummary}
                            loading={summaryLoadingFiles.has(currentFile?.id)}
                            disabled={!currentFile?.transcription || summaryLoadingFiles.has(currentFile?.id)}
                        >
                            {summaryLoadingFiles.has(currentFile?.id) ? '生成中...' : '生成总结'}
                        </Button>
                        <Button
                            onClick={() => handleExportSummary(currentFile?.summary)}
                            icon={<DownloadOutlined />}
                            disabled={!currentFile?.summary}
                        >
                            导出总结
                        </Button>
                    </div>
                    {!currentFile ? (
                        <div className="empty-state">
                            <p>请在左侧选择要查看总结的文件</p>
                        </div>
                    ) : !currentFile.transcription ? (
                        <div className="empty-state">
                            <p>当前文件尚未完成转录</p>
                        </div>
                    ) : !currentFile.summary ? (
                        <div className="empty-state">
                            <p>点击上方按钮生成简单总结</p>
                        </div>
                    ) : (
                        <SummaryContent
                            fileId={currentFile.id}
                            content={currentFile.summary}
                            isLoading={summaryLoadingFiles.has(currentFile.id)}
                        />
                    )}
                </div>
            ),
        },
        {
            key: '3',
            label: '详细总结',
            children: (
                <div className="tab-content">
                    {currentFile && (
                        <div className="current-file-tip">
                            <span>当前文件：{currentFile.name}</span>
                        </div>
                    )}
                    <div className="button-group">
                        <Button
                            onClick={handleDetailedSummary}
                            loading={detailedSummaryLoadingFiles.has(currentFile?.id)}
                            disabled={!currentFile?.transcription || detailedSummaryLoadingFiles.has(currentFile?.id)}
                        >
                            {detailedSummaryLoadingFiles.has(currentFile?.id) ? '生成中...' : '生成详细总结'}
                        </Button>
                        <Button
                            onClick={() => handleExportSummary(currentFile?.detailedSummary, 'detailed_summary')}
                            icon={<DownloadOutlined />}
                            disabled={!currentFile?.detailedSummary}
                        >
                            导出总结
                        </Button>
                    </div>
                    {!currentFile ? (
                        <div className="empty-state">
                            <p>请在左侧选择要查看详细总结的文件</p>
                        </div>
                    ) : !currentFile.transcription ? (
                        <div className="empty-state">
                            <p>当前文件尚未完成转录</p>
                        </div>
                    ) : !currentFile.detailedSummary && !detailedSummaryLoadingFiles.has(currentFile.id) ? (
                        <div className="empty-state">
                            <p>点击上方按钮生成详细总结</p>
                        </div>
                    ) : (
                        <DetailedSummaryContent
                            fileId={currentFile.id}
                            content={currentFile.detailedSummary}
                            isLoading={detailedSummaryLoadingFiles.has(currentFile.id)}
                        />
                    )}
                </div>
            ),
        },
        {
            key: '4',
            label: '思维导图',
            children: (
                <div className="tab-content">
                    {currentFile && (
                        <div className="current-file-tip">
                            <span>当前文件：{currentFile.name}</span>
                        </div>
                    )}
                    <Button
                        onClick={handleMindmap}
                        loading={mindmapLoadingFiles.has(currentFile?.id)}
                        disabled={!currentFile?.transcription || mindmapLoadingFiles.has(currentFile?.id)}
                    >
                        {mindmapLoadingFiles.has(currentFile?.id) ? '生成中...' : '生成思维导图'}
                    </Button>
                    {!currentFile ? (
                        <div className="empty-state">
                            <p>请在左侧选择要查看思维导图的文件</p>
                        </div>
                    ) : !currentFile.transcription ? (
                        <div className="empty-state">
                            <p>当前文件尚未完成转录</p>
                        </div>
                    ) : !currentFile.mindmapData && !mindmapLoadingFiles.has(currentFile.id) ? (
                        <div className="empty-state">
                            <p>点击上方按钮生成思维导图</p>
                        </div>
                    ) : (
                        <MindmapContent
                            fileId={currentFile.id}
                            content={currentFile.mindmapData}
                            isLoading={mindmapLoadingFiles.has(currentFile.id)}
                        />
                    )}
                </div>
            ),
        },
        {
            key: '5',
            label: '对话交互',
            children: (
                <div className="tab-content chat-tab">
                    {!currentFile ? (
                        <div className="empty-state">
                            <p>请在左侧选择要查看对话交互的文件</p>
                        </div>
                    ) : !currentFile.transcription ? (
                        <div className="empty-state">
                            <p>当前文件尚未完成转录</p>
                        </div>
                    ) : (
                        <>
                            <div className="current-file-tip">
                                <span>当前文件：{currentFile.name}</span>
                            </div>
                            <div
                                className="chat-messages"
                                onScroll={handleScroll}
                            >
                                {messages.map((msg, index) => (
                                    <div
                                        key={index}
                                        className={`message-wrapper ${msg.role === 'user' ? 'user' : 'assistant'}`}
                                    >
                                        <div className="message-bubble">
                                            <div className="message-content">
                                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                                            </div>
                                            <Button
                                                type="text"
                                                className="copy-button"
                                                icon={<CopyOutlined />}
                                                onClick={() => handleCopyMessage(msg.content)}
                                            >
                                                复制
                                            </Button>
                                        </div>
                                        <div className="message-time">
                                            {new Date().toLocaleTimeString()}
                                        </div>
                                    </div>
                                ))}
                                <div ref={messagesEndRef} />
                            </div>
                            <div className="chat-input-area">
                                <TextArea
                                    value={inputMessage}
                                    onChange={e => setInputMessage(e.target.value)}
                                    onCompositionStart={() => setIsComposing(true)}
                                    onCompositionEnd={() => setIsComposing(false)}
                                    onKeyDown={e => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            if (!isComposing) {
                                                e.preventDefault();
                                                handleSendMessage();
                                            }
                                        }
                                    }}
                                    placeholder="输入消息按Enter发送，Shift+Enter换行"
                                    autoSize={{ minRows: 1, maxRows: 4 }}
                                    disabled={isGenerating}
                                />
                                <Button
                                    type="primary"
                                    icon={isGenerating ? <StopOutlined /> : <SendOutlined />}
                                    onClick={handleSendMessage}
                                    danger={isGenerating}
                                >
                                    {isGenerating ? '停止' : '发送'}
                                </Button>
                            </div>
                        </>
                    )}
                </div>
            ),
        },
        {
            key: '6',
            label: '多模态分析',
            children: (
                <div className="tab-content">
                    {currentFile && (
                        <div className="current-file-tip">
                            <span>当前文件：{currentFile.name}</span>
                        </div>
                    )}
                    <div className="button-group">
                        <Button
                            onClick={handleMultimodalAnalysis}
                            loading={multimodalLoadingFiles.has(currentFile?.id)}
                            disabled={!currentFile?.transcription || multimodalLoadingFiles.has(currentFile?.id)}
                        >
                            {multimodalLoadingFiles.has(currentFile?.id) ? '分析中...' : '开始多模态分析'}
                        </Button>
                    </div>
                    {!currentFile ? (
                        <div className="empty-state">
                            <p>请在左侧选择要进行多模态分析的文件</p>
                        </div>
                    ) : !currentFile.transcription ? (
                        <div className="empty-state">
                            <p>当前文件尚未完成转录</p>
                        </div>
                    ) : !currentFile.multimodalAnalysis && !multimodalLoadingFiles.has(currentFile.id) ? (
                        <div className="empty-state">
                            <p>点击上方按钮开始多模态分析</p>
                        </div>
                    ) : multimodalLoadingFiles.has(currentFile.id) ? (
                        <div className="empty-state">
                            <div className="loading-spinner"></div>
                            <p>正在进行多模态分析，请稍候...</p>
                        </div>
                    ) : (
                        <div className="multimodal-analysis-content">
                            <h3>分析结果</h3>
                            <p><strong>视频时长：</strong>{currentFile.multimodalAnalysis.video_info.duration.toFixed(2)}秒</p>
                            <p><strong>分辨率：</strong>{currentFile.multimodalAnalysis.video_info.width}x{currentFile.multimodalAnalysis.video_info.height}</p>
                            <p><strong>帧率：</strong>{currentFile.multimodalAnalysis.video_info.fps.toFixed(1)}fps</p>
                            <p><strong>截图数量：</strong>{currentFile.multimodalAnalysis.screenshot_count}张</p>

                            <h3>分析总结</h3>
                            <ReactMarkdown>{currentFile.multimodalAnalysis.analysis.summary}</ReactMarkdown>
                        </div>
                    )}
                </div>
            ),
        },
        {
            key: '7',
            label: '综合报告',
            children: (
                <div className="tab-content">
                    {currentFile && (
                        <div className="current-file-tip">
                            <span>当前文件：{currentFile.name}</span>
                        </div>
                    )}
                    <div className="button-group">
                        <Button
                            onClick={handleComprehensiveAnalysis}
                            loading={comprehensiveLoadingFiles.has(currentFile?.id)}
                            disabled={!currentFile?.transcription || comprehensiveLoadingFiles.has(currentFile?.id)}
                        >
                            {comprehensiveLoadingFiles.has(currentFile?.id) ? '分析中...' : '开始综合分析'}
                        </Button>
                        {currentFile?.comprehensiveAnalysis && (
                            <Button
                                onClick={handleExportComprehensiveAnalysis}
                                icon={<DownloadOutlined />}
                            >
                                导出Markdown
                            </Button>
                        )}
                    </div>
                    {!currentFile ? (
                        <div className="empty-state">
                            <p>请在左侧选择要进行综合分析的文件</p>
                        </div>
                    ) : !currentFile.transcription ? (
                        <div className="empty-state">
                            <p>当前文件尚未完成转录</p>
                        </div>
                    ) : !currentFile.comprehensiveAnalysis && !comprehensiveLoadingFiles.has(currentFile.id) ? (
                        <div className="empty-state">
                            <p>点击上方按钮开始综合分析</p>
                            <p>综合分析包含：详细总结 + 多模态分析 + 视频统计</p>
                        </div>
                    ) : comprehensiveLoadingFiles.has(currentFile.id) ? (
                        <div className="empty-state">
                            <div className="loading-spinner"></div>
                            <p>正在进行综合分析，请稍候...</p>
                            <p>分析过程包括：多模态分析 + 详细总结生成</p>
                        </div>
                    ) : (
                        <div className="comprehensive-analysis-content">
                            <h3>视频信息统计</h3>
                            <p><strong>时长：</strong>{currentFile.comprehensiveAnalysis.video_info.duration.toFixed(2)}秒</p>
                            <p><strong>分辨率：</strong>{currentFile.comprehensiveAnalysis.video_info.width}x{currentFile.comprehensiveAnalysis.video_info.height}</p>
                            <p><strong>帧率：</strong>{currentFile.comprehensiveAnalysis.video_info.fps.toFixed(1)}fps</p>
                            <p><strong>截图数量：</strong>{currentFile.comprehensiveAnalysis.statistics.screenshot_count}张</p>
                            <p><strong>OCR识别数：</strong>{currentFile.comprehensiveAnalysis.statistics.ocr_count}张</p>
                            <p><strong>字幕数：</strong>{currentFile.comprehensiveAnalysis.statistics.subtitle_count}条</p>

                            <h3>详细总结</h3>
                            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#f5f5f5', padding: '12px', borderRadius: '4px', maxHeight: '400px', overflowY: 'auto' }}>
                                {currentFile.comprehensiveAnalysis.detailed_summary}
                            </pre>

                            <h3>多模态分析总结</h3>
                            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#f5f5f5', padding: '12px', borderRadius: '4px', maxHeight: '400px', overflowY: 'auto' }}>
                                {currentFile.comprehensiveAnalysis.analysis_summary}
                            </pre>
                        </div>
                    )}
                </div>
            ),
        },
    ];

    // 修改左侧标签页内容
    const leftTabItems = [
        {
            key: '1',
            label: '音视频预览',
            children: (
                <div className="tab-content">
                    <div className="preview-section">
                        {mediaUrl ? (
                            <div className="media-preview">
                                {mediaUrl.type === 'video' ? (
                                    <div className="video-container">
                                        <video
                                            ref={mediaRef}
                                            src={mediaUrl.url}
                                            controls
                                            className="video-player"
                                        />
                                    </div>
                                ) : (
                                    <div className="audio-container">
                                        <div className="audio-placeholder">
                                            <SoundOutlined style={{ fontSize: '24px' }} />
                                            <span>音频文件</span>
                                        </div>
                                        <audio
                                            ref={mediaRef}
                                            src={mediaUrl.url}
                                            controls
                                            className="audio-player"
                                        />
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="upload-placeholder">
                                <div className="placeholder-content">
                                    <div className="placeholder-icon">
                                        <UploadOutlined style={{ fontSize: '48px', color: '#999' }} />
                                    </div>
                                    <p>等待上传本地文件</p>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="file-list-section">
                        <div className="section-header">
                            <div className="section-title">
                                <h3>文件列表</h3>
                            </div>
                            <div className="action-buttons">
                                <Button
                                    onClick={() => {
                                        const allFileIds = uploadedFiles.map(file => file.id);
                                        setSelectedFiles(allFileIds);
                                    }}
                                >
                                    全选
                                </Button>
                                <Button
                                    onClick={() => setSelectedFiles([])}
                                >
                                    取消全选
                                </Button>
                                <Button
                                    type="primary"
                                    danger
                                    onClick={handleDeleteAll}
                                    disabled={selectedFiles.length === 0 || selectedFiles.some(id =>
                                        uploadedFiles.find(f => f.id === id)?.status === 'transcribing'
                                    )}
                                >
                                    删除选中
                                </Button>
                                <Button
                                    type="primary"
                                    onClick={handleBatchTranscribe}
                                    disabled={selectedFiles.length === 0}
                                    danger={isTranscribing}
                                >
                                    {isTranscribing ? '停止转录' : '开始转录'}
                                </Button>
                            </div>
                        </div>
                        <Table
                            rowSelection={{
                                selectedRowKeys: selectedFiles,
                                onChange: handleFileSelect,
                                preserveSelectedRowKeys: true,
                            }}
                            dataSource={getPageData()} // 使用分页后的数据
                            columns={fileColumns}
                            rowKey="id"
                            size="small"
                            onRow={(record) => ({
                                onClick: () => handleFilePreview(record),
                                style: {
                                    cursor: 'pointer',
                                    background: currentFile?.id === record.id ? '#e6f7ff' : 'inherit',
                                },
                            })}
                            pagination={false}
                        />
                        <div className="pagination-container">
                            <Pagination
                                {...paginationConfig}
                                total={uploadedFiles.length}
                            />
                        </div>
                    </div>
                </div>
            ),
        },
    ];

    return (
        <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
            <div className="app-header" style={{ background: '#fff' }}>
                <div className="title">
                    <h1 style={{ color: '#000' }}>VideoChat：一键总结视频与音频内容｜帮助解读的 AI 助手</h1>
                </div>
                <div className="header-right">
                    <a
                        href="https://github.com/Airmomo/VideoChat"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="github-link"
                    >
                        <GithubOutlined />
                        <span className="author-info">By Airmomo</span>
                    </a>
                </div>
                <div className="upload-section">
                    <Upload
                        beforeUpload={handleUpload}
                        accept="video/*,audio/*"
                        showUploadList={false}
                        multiple={true}
                        directory={false}
                    >
                        <Button icon={<UploadOutlined />}>
                            上传本地文件
                        </Button>
                    </Upload>
                </div>
                <div className="support-text">
                    支持多个视频和音频文件格式
                </div>
            </div>

            <div className="app-content">
                <div className="main-layout">
                    <div className="media-panel">
                        <Card className="media-card">
                            <Tabs items={leftTabItems} />
                        </Card>
                    </div>

                    <div className="feature-panel">
                        <Card className="feature-card">
                            <Tabs items={tabItems} />
                        </Card>
                    </div>
                </div>
            </div>
        </Layout>
    );
}

export default App;
