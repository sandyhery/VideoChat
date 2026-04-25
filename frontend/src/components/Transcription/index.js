import React from 'react';
import { Table, Button } from 'antd';

const Transcription = ({ transcription, onTimeClick }) => {
  // 时间格式化函数
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
          onClick={() => onTimeClick(record.start)}
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

  if (!transcription || transcription.length === 0) {
    return <div className="transcription">暂无转录结果</div>;
  }

  return (
    <div className="transcription">
      <Table
        columns={transcriptionColumns}
        dataSource={transcription}
        rowKey={(record, index) => index}
        pagination={false}
      />
    </div>
  );
};

export default Transcription;