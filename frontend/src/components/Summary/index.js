import React from 'react';
import ReactMarkdown from 'react-markdown';

const Summary = ({ content, isLoading }) => {
  if (isLoading) {
    return <div className="summary-loading">正在生成总结...</div>;
  }

  if (!content) {
    return <div className="summary">暂无总结内容</div>;
  }

  return (
    <div className="summary markdown-content">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
};

export default Summary;