import React from 'react';
import { Upload, Button, Table, message } from 'antd';
import { UploadOutlined, DeleteOutlined, SyncOutlined } from '@ant-design/icons';

const FileUploader = ({ 
  uploadedFiles, 
  selectedFiles, 
  isTranscribing, 
  onFileUpload, 
  onFileSelect, 
  onFileDelete, 
  onFilePreview, 
  onBatchTranscribe,
  pageSize,
  currentPage,
  onPageChange,
  onPageSizeChange,
  getPageData
}) => {
  // 处理文件上传
  const handleUpload = async (options) => {
    const { file, onSuccess, onError, onProgress } = options;
    try {
      onFileUpload(file);
      message.success('文件上传成功');
      onSuccess();
    } catch (error) {
      message.error(error.message || '上传失败');
      onError(error);
    }
    return false; // 阻止自动上传
  };

  // 处理表格行点击
  const handleRowClick = (record) => {
    onFilePreview(record);
  };

  // 处理批量转录按钮点击
  const handleTranscribeClick = async () => {
    try {
      const result = await onBatchTranscribe();
      message.success(result);
    } catch (error) {
      message.error(error.message);
    }
  };

  // 文件列表列定义
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
            onFileDelete(record.id);
            message.success('文件删除成功');
          }}
          icon={<DeleteOutlined />}
          disabled={record.status === 'transcribing'}
        >
          删除
        </Button>
      ),
    },
  ];

  // 分页配置
  const paginationConfig = {
    current: currentPage,
    pageSize: pageSize,
    showSizeChanger: true,
    pageSizeOptions: ['5', '10', '20', '50'],
    showTotal: (total) => `共 ${total} 个文件`,
    onChange: (page, size) => {
      onPageChange(page);
      onPageSizeChange(size);
    },
    onShowSizeChange: (current, size) => {
      onPageChange(1);
      onPageSizeChange(size);
    },
  };

  return (
    <div className="file-uploader">
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Upload
          name="file"
          accept="video/*,audio/*"
          showUploadList={false}
          customRequest={handleUpload}
        >
          <Button icon={<UploadOutlined />}>上传视频/音频文件</Button>
        </Upload>
        <Button 
          type={isTranscribing ? "danger" : "primary"}
          onClick={handleTranscribeClick}
          loading={isTranscribing}
        >
          {isTranscribing ? '停止转录' : '批量转录'}
        </Button>
      </div>
      
      <Table
        rowSelection={{
          selectedRowKeys: selectedFiles,
          onChange: onFileSelect,
        }}
        columns={fileColumns}
        dataSource={getPageData()}
        rowKey="id"
        pagination={paginationConfig}
        onRow={(record) => ({
          onClick: () => handleRowClick(record),
        })}
      />
    </div>
  );
};

export default FileUploader;