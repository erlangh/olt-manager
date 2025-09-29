import React from 'react';
import { Layout, Avatar, Dropdown, Button, Badge, Space, Typography } from 'antd';
import {
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  BellOutlined,
  SunOutlined,
  MoonOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { useNavigate } from 'react-router-dom';

const { Header } = Layout;
const { Text } = Typography;

const AppHeader = ({ collapsed, onToggle }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { isConnected } = useWebSocket();
  const navigate = useNavigate();

  // User menu items
  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
      onClick: () => navigate('/profile'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      onClick: logout,
    },
  ];

  // Notification menu items (placeholder)
  const notificationItems = [
    {
      key: 'no-notifications',
      label: (
        <div style={{ padding: '8px 0', textAlign: 'center' }}>
          <Text type="secondary">No new notifications</Text>
        </div>
      ),
    },
  ];

  return (
    <Header className="app-header">
      <div className="header-left">
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={onToggle}
          className="sidebar-toggle"
        />
        
        <div className="header-title">
          <Text strong>OLT Manager</Text>
        </div>
      </div>

      <div className="header-right">
        <Space size="middle">
          {/* Connection Status */}
          <div className="connection-status">
            <Badge 
              status={isConnected ? 'success' : 'error'} 
              text={isConnected ? 'Connected' : 'Disconnected'}
            />
          </div>

          {/* Theme Toggle */}
          <Button
            type="text"
            icon={theme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          />

          {/* Notifications */}
          <Dropdown
            menu={{ items: notificationItems }}
            placement="bottomRight"
            trigger={['click']}
          >
            <Button type="text" icon={<BellOutlined />}>
              <Badge count={0} size="small" />
            </Button>
          </Dropdown>

          {/* User Menu */}
          <Dropdown
            menu={{ items: userMenuItems }}
            placement="bottomRight"
            trigger={['click']}
          >
            <div className="user-info">
              <Avatar 
                size="small" 
                icon={<UserOutlined />}
                src={user?.avatar}
              />
              <span className="username">{user?.full_name || user?.username}</span>
            </div>
          </Dropdown>
        </Space>
      </div>
    </Header>
  );
};

export default AppHeader;