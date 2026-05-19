import React, { useEffect, useState, useRef } from 'react';
import { Drawer, Spin, Typography, Empty, Tag } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import { documentApi } from '../../services/api';
import styles from './index.module.less';

interface Props {
  open: boolean;
  onClose: () => void;
  knowledgeBaseId: number | null;
  filename: string;
  snippet: string;
  page: number;
}

export default function DocumentViewer({ open, onClose, knowledgeBaseId, filename, snippet, page }: Props) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [docFilename, setDocFilename] = useState('');
  const highlightRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open || !knowledgeBaseId || !filename) return;

    const fetchContent = async () => {
      setLoading(true);
      try {
        // Try by source_filename first (handles UUID-prefixed filenames from vector store)
        const { data } = await documentApi.getContentBySource(knowledgeBaseId, filename);
        setContent(data.content);
        setDocFilename(data.filename);
      } catch {
        // Fallback: try matching by document list
        try {
          const { data: docs } = await documentApi.list(knowledgeBaseId);
          const targetDoc = docs.find((d) => filename.includes(d.filename) || d.filename.includes(filename));
          if (targetDoc) {
            const { data } = await documentApi.getContent(knowledgeBaseId, targetDoc.id);
            setContent(data.content);
            setDocFilename(data.filename);
          } else {
            setContent('');
            setDocFilename(filename);
          }
        } catch {
          setContent('');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchContent();
  }, [open, knowledgeBaseId, filename]);

  // Scroll to highlighted section after content loads
  useEffect(() => {
    if (content && highlightRef.current) {
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    }
  }, [content, snippet]);

  const renderContent = () => {
    if (loading) return <Spin style={{ display: 'block', margin: '40px auto' }} />;
    if (!content) return <Empty description="无法加载文档内容" />;

    // Find and highlight the snippet in the content
    const snippetClean = snippet.replace(/\s+/g, ' ').trim().slice(0, 60);
    const matchIndex = content.indexOf(snippetClean);

    if (matchIndex === -1) {
      // Fallback: try matching first 30 chars
      const shortSnippet = snippet.replace(/\s+/g, ' ').trim().slice(0, 30);
      const fallbackIndex = content.indexOf(shortSnippet);

      if (fallbackIndex === -1) {
        return (
          <div className={styles.docContent}>
            <pre className={styles.preText}>{content}</pre>
          </div>
        );
      }

      const before = content.slice(0, fallbackIndex);
      const matched = content.slice(fallbackIndex, fallbackIndex + snippet.length);
      const after = content.slice(fallbackIndex + snippet.length);

      return (
        <div className={styles.docContent}>
          <pre className={styles.preText}>
            {before}
            <span ref={highlightRef} className={styles.highlight}>{matched}</span>
            {after}
          </pre>
        </div>
      );
    }

    const before = content.slice(0, matchIndex);
    const matched = content.slice(matchIndex, matchIndex + snippet.length);
    const after = content.slice(matchIndex + snippet.length);

    return (
      <div className={styles.docContent}>
        <pre className={styles.preText}>
          {before}
          <span ref={highlightRef} className={styles.highlight}>{matched}</span>
          {after}
        </pre>
      </div>
    );
  };

  return (
    <Drawer
      title={
        <span>
          <FileTextOutlined style={{ marginRight: 8 }} />
          {docFilename || filename}
          <Tag color="geekblue" style={{ marginLeft: 8 }}>第 {page} 页</Tag>
        </span>
      }
      open={open}
      onClose={onClose}
      width={600}
      destroyOnClose
    >
      {renderContent()}
    </Drawer>
  );
}
