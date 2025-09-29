import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, Alert, Divider, Space } from 'antd';
import { UserOutlined, LockOutlined, RouterOutlined } from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';

const { Title, Text } = Typography;

const Login = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Get redirect path from location state or default to dashboard
  const from = location.state?.from?.pathname || '/dashboard';

  const handleSubmit = async (values) => {
    setLoading(true);
    setError('');

    try {
      const result = await login(values);
      
      if (result.success) {
        navigate(from, { replace: true });
      } else {
        setError(result.error || 'Login gagal. Silakan coba lagi.');
      }
    } catch (err) {
      setError('Terjadi kesalahan. Silakan coba lagi.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-background">
        <div className="login-overlay" />
      </div>
      
      <div className="login-content">
        <Card className="login-card" bordered={false}>
          <div className="login-header">
            <div className="login-logo">
              <RouterOutlined className="logo-icon" />
            </div>
            <Title level={2} className="login-title">
              OLT Manager
            </Title>
            <Text type="secondary" className="login-subtitle">
              ZTE C320 Management System
            </Text>
          </div>

          <Divider />

          {error && (
            <Alert
              message={error}
              type="error"
              showIcon
              closable
              onClose={() => setError('')}
              style={{ marginBottom: 24 }}
            />
          )}

          <Form
            form={form}
            name="login"
            onFinish={handleSubmit}
            layout="vertical"
            size="large"
            autoComplete="off"
          >
            <Form.Item
              name="username"
              label="Username"
              rules={[
                {
                  required: true,
                  message: 'Silakan masukkan username!',
                },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="Masukkan username"
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              name="password"
              label="Password"
              rules={[
                {
                  required: true,
                  message: 'Silakan masukkan password!',
                },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Masukkan password"
                autoComplete="current-password"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                size="large"
              >
                {loading ? 'Logging in...' : 'Login'}
              </Button>
            </Form.Item>
          </Form>

          <div className="login-footer">
            <Space direction="vertical" size="small" style={{ width: '100%', textAlign: 'center' }}>
              <Text type="secondary">
                Default credentials for testing:
              </Text>
              <Text code>admin / admin123</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                OLT Manager v1.0 - ZTE C320 Management System
              </Text>
            </Space>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Login;