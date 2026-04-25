import React, { useEffect } from 'react';
import jsMind from 'jsmind';
import 'jsmind/style/jsmind.css';

const Mindmap = ({ content, isLoading, fileId }) => {
  const containerId = `mindmap-container-${fileId || 'default'}`;

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
  return <div id={containerId} className="mindmap-container">暂无思维导图数据</div>;
};

export default Mindmap;