import React from 'react';
import MarkdownViewer from '@seafile/seafile-editor/dist/viewer/markdown-viewer';

import '../../css/md-file-view.css';

const { fileContent } = window.app.pageOptions;

class FileContent extends React.Component {
  render() {
    return (
      <div className="file-view-content flex-1">
        <div className="md-content">
          <MarkdownViewer 
            markdownContent={fileContent}
            showTOC={false}
          />
        </div>
      </div>
    );
  }
}

export default FileContent;
