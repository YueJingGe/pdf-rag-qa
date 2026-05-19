import React, { useState, useEffect } from 'react';
import { Layout, Tabs, Dropdown, Button, Avatar, Space, message } from 'antd';
import {
  MessageOutlined, FileOutlined, UserOutlined, LogoutOutlined,
  BarChartOutlined, LoginOutlined,
} from '@ant-design/icons';
import KnowledgeBaseSidebar from './components/KnowledgeBaseSidebar';
import DocumentUpload from './components/DocumentUpload';
import ChatWindow from './components/ChatWindow';
import LoginModal from './components/LoginModal';
import FeedbackDashboard from './components/FeedbackDashboard';
import DocumentViewer from './components/DocumentViewer';
import type { CitationClickInfo } from './components/CitationView';
import { authApi, type KnowledgeBase, type UserInfo } from './services/api';

const { Sider, Content, Header } = Layout;

export default function App() {
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(() => {
    const saved = localStorage.getItem('selectedKB');
    return saved ? JSON.parse(saved) : null;
  });
  const [activeTab, setActiveTab] = useState('chat');
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerCitation, setViewerCitation] = useState<CitationClickInfo>({ filename: '', page: 0, snippet: '' });

  const refreshSidebar = () => setSidebarRefreshKey((k) => k + 1);

  const handleCitationClick = (info: CitationClickInfo) => {
    setViewerCitation(info);
    setViewerOpen(true);
  };

  // Persist selectedKB to localStorage
  useEffect(() => {
    if (selectedKB) {
      localStorage.setItem('selectedKB', JSON.stringify(selectedKB));
    } else {
      localStorage.removeItem('selectedKB');
    }
  }, [selectedKB]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      authApi.getMe().then(({ data }) => setUser(data)).catch(() => {
        localStorage.removeItem('token');
      });
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
    message.success('已退出登录');
  };

  const handleLoginSuccess = (userInfo: UserInfo, token: string) => {
    localStorage.setItem('token', token);
    setUser(userInfo);
    setLoginOpen(false);
    message.success(`欢迎回来，${userInfo.display_name}`);
  };

  const userRole = user?.is_admin ? 'owner' : 'member';
  const canManageDocs = userRole === 'owner' || userRole === 'member';

  const isPlainChat = !selectedKB;

  // Switch to chat tab when entering plain chat mode
  useEffect(() => {
    if (isPlainChat && activeTab !== 'chat') {
      setActiveTab('chat');
    }
  }, [isPlainChat, activeTab]);

  const tabItems = [
    {
      key: 'chat',
      label: <span><MessageOutlined /> {isPlainChat ? '普通聊天' : '智能问答'}</span>,
      children: (
        <div style={{ height: 'calc(100vh - 112px)', overflow: 'hidden' }}>
          <ChatWindow
            knowledgeBaseId={selectedKB?.id ?? null}
            knowledgeBaseName={selectedKB?.name ?? ''}
            userRole={userRole}
            onCitationClick={handleCitationClick}
          />
        </div>
      ),
    },
    ...(canManageDocs && !isPlainChat ? [{
      key: 'docs',
      label: <span><FileOutlined /> 文档管理</span>,
      children: (
        <div style={{ height: 'calc(100vh - 112px)', overflow: 'hidden' }}>
          <DocumentUpload knowledgeBaseId={selectedKB?.id ?? null} onDocChange={refreshSidebar} />
        </div>
      ),
    }] : []),
    ...(user?.is_admin && !isPlainChat ? [{
      key: 'feedback',
      label: <span><BarChartOutlined /> 检索调优</span>,
      children: (
        <div style={{ height: 'calc(100vh - 112px)', overflow: 'auto', padding: 16 }}>
          <FeedbackDashboard knowledgeBaseId={selectedKB?.id ?? null} />
        </div>
      ),
    }] : []),
  ];

  return (
    <Layout style={{ height: '100vh', overflow: 'hidden' }}>
      <Header style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: 56 }}>
        <span style={{ fontSize: 16, fontWeight: 600 }}>📚 PDF RAG 智能问答系统</span>
        <Space>
          {user ? (
            <Dropdown menu={{ items: [
              { key: 'role', label: `角色: ${user.is_admin ? '管理员' : '成员'}`, disabled: true },
              { key: 'logout', label: '退出登录', icon: <LogoutOutlined />, onClick: handleLogout },
            ]}} placement="bottomRight">
              <Button type="text">
                <Avatar size="small" icon={<UserOutlined />} style={{ marginRight: 6 }} />
                {user.display_name}
              </Button>
            </Dropdown>
          ) : (
            <Button type="primary" icon={<LoginOutlined />} onClick={() => setLoginOpen(true)}>
              登录
            </Button>
          )}
        </Space>
      </Header>
      <Layout style={{ flex: 1, overflow: 'hidden' }}>
        <Sider width={280} style={{ background: '#fff', borderRight: '1px solid #f0f0f0', overflow: 'auto' }}>
          <KnowledgeBaseSidebar
            selectedId={selectedKB?.id ?? null}
            onSelect={(kb) => setSelectedKB(kb ?? null)}
            refreshKey={sidebarRefreshKey}
          />
        </Sider>
        <Content style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            centered
            style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            items={tabItems}
          />
        </Content>
      </Layout>
      <LoginModal open={loginOpen} onCancel={() => setLoginOpen(false)} onSuccess={handleLoginSuccess} />
      <DocumentViewer
        open={viewerOpen}
        onClose={() => setViewerOpen(false)}
        knowledgeBaseId={selectedKB?.id ?? null}
        filename={viewerCitation.filename}
        snippet={viewerCitation.snippet}
        page={viewerCitation.page}
      />
    </Layout>
  );
}
