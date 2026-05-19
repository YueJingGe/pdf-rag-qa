import React, { useState } from 'react';
import { Modal, Form, Input, Button, Tabs, message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { authApi, type UserInfo } from '../../services/api';

interface Props {
  open: boolean;
  onCancel: () => void;
  onSuccess: (user: UserInfo, token: string) => void;
}

export default function LoginModal({ open, onCancel, onSuccess }: Props) {
  const [loading, setLoading] = useState(false);
  const [loginForm] = Form.useForm();
  const [registerForm] = Form.useForm();

  const handleLogin = async () => {
    const values = await loginForm.validateFields();
    setLoading(true);
    try {
      const { data } = await authApi.login(values.username, values.password);
      onSuccess(data.user, data.access_token);
    } catch {
      message.error('用户名或密码错误');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    const values = await registerForm.validateFields();
    setLoading(true);
    try {
      await authApi.register(values);
      message.success('注册成功，请登录');
      registerForm.resetFields();
    } catch {
      message.error('注册失败，用户名或邮箱已存在');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onCancel={onCancel} footer={null} title="用户认证" destroyOnClose width={400}>
      <Tabs
        centered
        items={[
          {
            key: 'login',
            label: '登录',
            children: (
              <Form form={loginForm} onFinish={handleLogin} layout="vertical">
                <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                  <Input prefix={<UserOutlined />} placeholder="用户名" />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                  <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                </Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block>
                  登录
                </Button>
              </Form>
            ),
          },
          {
            key: 'register',
            label: '注册',
            children: (
              <Form form={registerForm} onFinish={handleRegister} layout="vertical">
                <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                  <Input prefix={<UserOutlined />} placeholder="用户名" />
                </Form.Item>
                <Form.Item name="email" rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}>
                  <Input prefix={<MailOutlined />} placeholder="邮箱" />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
                  <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                </Form.Item>
                <Form.Item name="display_name">
                  <Input prefix={<UserOutlined />} placeholder="显示名称（可选）" />
                </Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block>
                  注册
                </Button>
              </Form>
            ),
          },
        ]}
      />
    </Modal>
  );
}
