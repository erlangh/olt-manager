import React, { useState, useEffect } from 'react';
import { Layout, Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  RouterOutlined,
  WifiOutlined,
  MonitorOutlined,
  BellOutlined,
  SettingOutlined,
  BackupOutlined,
  ProfileOutlined,
  UserOutlined,
  FileTextOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';

const { Sider } = Layout;

const AppSider = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { user, hasRole } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Get current selected menu key based on pathname
  const getSelectedKey = () => {
    const pathname = location.pathname;
    if (pathname === '/' || pathname === '/dashboard') return 'dashboard';
    if (pathname.startsWith('/olts')) return 'olts';
    if (pathname.startsWith('/onts')) return 'onts';
    if (pathname.startsWith('/monitoring')) return 'monitoring';
    if (pathname.startsWith('/alarms')) return 'alarms';
    if (pathname.startsWith('/configuration')) return 'configuration';
    if (pathname.startsWith('/backup-restore')) return 'backup-restore';
    if (pathname.startsWith('/service-profiles')) return 'service-profiles';
    if (pathname.startsWith('/users')) return 'users';
    if (pathname.startsWith('/reports')) return 'reports';
    if (pathname.startsWith('/settings')) return 'settings';
    return 'dashboard';
  };

  const [selectedKey, setSelectedKey] = useState(getSelectedKey());

  // Update selected key when location changes
  useEffect(() => {
    setSelectedKey(getSelectedKey());
  }, [location.pathname]);

  // Menu items configuration
  const getMenuItems = () => {
    const items = [
      {
        key: 'dashboard',
        icon: <DashboardOutlined />,
        label: 'Dashboard',
      },
      {
        key: 'olt-management',
        icon: <RouterOutlined />,
        label: 'OLT Management',
        children: [
          {
            key: 'olts',
            label: 'OLT List',
          },
        ],
      },
      {
        key: 'ont-management',
        icon: <WifiOutlined />,
        label: 'ONT Management',
        children: [
          {
            key: 'onts',
            label: 'ONT List',
          },
        ],
      },
      {
        key: 'monitoring-group',
        icon: <MonitorOutlined />,
        label: 'Monitoring',
        children: [
          {
            key: 'monitoring',
            label: 'Performance',
          },
          {
            key: 'alarms',
            label: 'Alarms',
          },
        ],
      },
      {
        key: 'configuration-group',
        icon: <SettingOutlined />,
        label: 'Configuration',
        children: [
          {
            key: 'configuration',
            label: 'OLT Config',
          },
          {
            key: 'service-profiles',
            label: 'Service Profiles',
          },
          ...(hasRole('admin') ? [{
            key: 'backup-restore',
            label: 'Backup & Restore',
          }] : []),
        ],
      },
      ...(hasRole('admin') ? [{
        key: 'user-management',
        icon: <UserOutlined />,
        label: 'User Management',
        children: [
          {
            key: 'users',
            label: 'Users',
          },
        ],
      }] : []),
      {
        key: 'reports-group',
        icon: <FileTextOutlined />,
        label: 'Reports',
        children: [
          {
            key: 'reports',
            label: 'Analytics',
          },
        ],
      },
      ...(hasRole('admin') ? [{
        key: 'system-group',
        icon: <ToolOutlined />,
        label: 'System',
        children: [
          {
            key: 'settings',
            label: 'Settings',
          },
        ],
      }] : []),
    ];

    return items;
  };

  // Handle menu click
  const handleMenuClick = ({ key }) => {
    setSelectedKey(key);
    
    switch (key) {
      case 'dashboard':
        navigate('/dashboard');
        break;
      case 'olts':
        navigate('/olts');
        break;
      case 'onts':
        navigate('/onts');
        break;
      case 'monitoring':
        navigate('/monitoring');
        break;
      case 'alarms':
        navigate('/alarms');
        break;
      case 'configuration':
        navigate('/configuration');
        break;
      case 'backup-restore':
        navigate('/backup-restore');
        break;
      case 'service-profiles':
        navigate('/service-profiles');
        break;
      case 'users':
        navigate('/users');
        break;
      case 'reports':
        navigate('/reports');
        break;
      case 'settings':
        navigate('/settings');
        break;
      default:
        break;
    }
  };

  // Get default open keys for submenus
  const getDefaultOpenKeys = () => {
    const pathname = location.pathname;
    const openKeys = [];
    
    if (pathname.startsWith('/olts')) openKeys.push('olt-management');
    if (pathname.startsWith('/onts')) openKeys.push('ont-management');
    if (pathname.startsWith('/monitoring') || pathname.startsWith('/alarms')) {
      openKeys.push('monitoring-group');
    }
    if (pathname.startsWith('/configuration') || 
        pathname.startsWith('/backup-restore') || 
        pathname.startsWith('/service-profiles')) {
      openKeys.push('configuration-group');
    }
    if (pathname.startsWith('/users')) openKeys.push('user-management');
    if (pathname.startsWith('/reports')) openKeys.push('reports-group');
    if (pathname.startsWith('/settings')) openKeys.push('system-group');
    
    return openKeys;
  };

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={setCollapsed}
      className="app-sider"
      width={250}
      theme="light"
    >
      <div className="logo">
        <div className="logo-icon">
          <RouterOutlined />
        </div>
        {!collapsed && (
          <div className="logo-text">
            <div className="logo-title">OLT Manager</div>
            <div className="logo-subtitle">ZTE C320</div>
          </div>
        )}
      </div>
      
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        defaultOpenKeys={getDefaultOpenKeys()}
        items={getMenuItems()}
        onClick={handleMenuClick}
        className="sidebar-menu"
      />
      
      {!collapsed && (
        <div className="sidebar-footer">
          <div className="user-badge">
            <div className="user-avatar">
              <UserOutlined />
            </div>
            <div className="user-details">
              <div className="user-name">{user?.full_name || user?.username}</div>
              <div className="user-role">{user?.role}</div>
            </div>
          </div>
        </div>
      )}
    </Sider>
  );
};

export default AppSider;