import React from 'react';
import { Card, Tag, Button, Space, Typography, message } from 'antd';
import { CheckOutlined, CloseOutlined } from '@ant-design/icons';
import type { RetrievalDebug } from '../../services/api';
import { feedbackApi } from '../../services/api';
import styles from './index.module.less';

interface Props {
  debug: RetrievalDebug;
  knowledgeBaseId: number;
  question: string;
  messageId: number;
}

export default function RetrievalDebugPanel({ debug, knowledgeBaseId, question, messageId }: Props) {
  const handleFeedback = async (chunkIndex: number, isRelevant: boolean) => {
    const chunk = debug.chunks[chunkIndex];
    try {
      await feedbackApi.create({
        message_id: messageId,
        knowledge_base_id: knowledgeBaseId,
        question,
        chunk_content: chunk.content,
        chunk_metadata: chunk.metadata,
        is_relevant: isRelevant,
      });
      message.success(isRelevant ? '已标记为相关' : '已标记为不相关');
    } catch {
      message.error('反馈提交失败');
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Tag color={debug.strategy === 'hyde' ? 'purple' : 'blue'}>
          {debug.strategy === 'hyde' ? 'HyDE 检索' : '向量检索'}
        </Tag>
        <Tag>{debug.retrieval_time_ms}ms</Tag>
        <Tag>{debug.chunks.length} chunks</Tag>
      </div>
      <div className={styles.chunkList}>
        {debug.chunks.map((chunk, index) => (
          <Card key={index} size="small" className={styles.chunkCard}>
            <div className={styles.chunkMeta}>
              <Tag color="geekblue">
                {(chunk.metadata.source_filename as string) || '未知文件'}
              </Tag>
              <Tag>第 {((chunk.metadata.page as number) || 0) + 1} 页</Tag>
            </div>
            <Typography.Paragraph
              ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
              className={styles.chunkContent}
            >
              {chunk.content}
            </Typography.Paragraph>
            <Space className={styles.feedbackBtns}>
              <Button
                size="small"
                type="text"
                icon={<CheckOutlined />}
                onClick={() => handleFeedback(index, true)}
                style={{ color: '#52c41a' }}
              >
                相关
              </Button>
              <Button
                size="small"
                type="text"
                icon={<CloseOutlined />}
                onClick={() => handleFeedback(index, false)}
                style={{ color: '#ff4d4f' }}
              >
                不相关
              </Button>
            </Space>
          </Card>
        ))}
      </div>
    </div>
  );
}
