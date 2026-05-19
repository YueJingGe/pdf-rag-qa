import React, { useEffect, useState } from 'react';
import { Card, Statistic, Row, Col, Empty, Typography, Table, Tag, Button, message } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, DownloadOutlined } from '@ant-design/icons';
import { feedbackApi, type FeedbackStats } from '../../services/api';

interface Props {
  knowledgeBaseId: number | null;
}

export default function FeedbackDashboard({ knowledgeBaseId }: Props) {
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [feedbacks, setFeedbacks] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    if (!knowledgeBaseId) return;
    setLoading(true);
    try {
      const [statsRes, exportRes] = await Promise.all([
        feedbackApi.stats(knowledgeBaseId),
        feedbackApi.export(knowledgeBaseId),
      ]);
      setStats(statsRes.data);
      setFeedbacks(exportRes.data as Array<Record<string, unknown>>);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setStats(null);
    setFeedbacks([]);
    fetchData();
  }, [knowledgeBaseId]);

  const handleExportJson = () => {
    if (!feedbacks.length) return;
    const blob = new Blob([JSON.stringify(feedbacks, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `feedback_kb${knowledgeBaseId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    message.success('导出成功');
  };

  if (!knowledgeBaseId) {
    return <Empty description="请先选择一个知识库" />;
  }

  const columns = [
    { title: '问题', dataIndex: 'question', key: 'question', ellipsis: true, width: 200 },
    { title: '文本块', dataIndex: 'chunk_content', key: 'chunk_content', ellipsis: true, width: 300 },
    {
      title: '相关性',
      dataIndex: 'is_relevant',
      key: 'is_relevant',
      width: 80,
      render: (val: boolean) => val
        ? <Tag icon={<CheckCircleOutlined />} color="success">相关</Tag>
        : <Tag icon={<CloseCircleOutlined />} color="error">不相关</Tag>,
    },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160 },
  ];

  return (
    <div>
      <Typography.Title level={4}>检索效果调优面板</Typography.Title>

      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card><Statistic title="总反馈数" value={stats.total} /></Card>
          </Col>
          <Col span={6}>
            <Card><Statistic title="相关" value={stats.relevant} valueStyle={{ color: '#3f8600' }} /></Card>
          </Col>
          <Col span={6}>
            <Card><Statistic title="不相关" value={stats.irrelevant} valueStyle={{ color: '#cf1322' }} /></Card>
          </Col>
          <Col span={6}>
            <Card><Statistic title="相关率" value={stats.relevance_rate * 100} suffix="%" precision={1} /></Card>
          </Col>
        </Row>
      )}

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Title level={5} style={{ margin: 0 }}>反馈记录</Typography.Title>
        <Button icon={<DownloadOutlined />} onClick={handleExportJson} disabled={!feedbacks.length}>
          导出 JSON（用于 Reranker 训练）
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={feedbacks.map((f, i) => ({ ...f, key: i }))}
        loading={loading}
        size="small"
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无反馈数据，请在对话中使用调试面板标记相关性' }}
      />
    </div>
  );
}
